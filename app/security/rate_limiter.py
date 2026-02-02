import ipaddress
import logging
from datetime import datetime
from hashlib import md5

import httpx
from fastapi import Request
from redis.asyncio import Redis

from app.config import config
from app.security.config import excluded_paths, private_paths, whitelistable_paths
from app.utils.request import ip_address

logger = logging.getLogger(__name__)


rate_limit_lua_script = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local expire_time = ARGV[2]

local current = tonumber(redis.call('GET', key) or "0")

-- If the key exists, and the count exceeds the limit, return the time until the key expires
-- Otherwise, increment the count and return 0
if current > 0 then
    if current + 1 > limit then
        return redis.call("PTTL", key)
    else
        redis.call("INCR", key)
        return 0
    end
-- If the key doesn't exist, set it to 1 and expire it
else
    redis.call("SET", key, 1, "EX", expire_time)
    return 0
end
"""


class RateLimiter:
    _script_sha: str
    _github_ips_key = "rate_limiter:github_ips"
    _github_ips_last_update_key = "rate_limiter:github_ips:last_update"

    def __init__(
        self,
        request: Request,
        limit: int,
        period: int,
        whitelist: list[str],
        github_ips_update_interval: int = 24 * 60 * 60,  # 24 hours
        redis: Redis = Redis.from_url(config.redis.dsn()),
    ):
        """
        :param request: The FastAPI request object
        :param redis: A Redis connection object
        :param limit: The number of requests allowed in the period
        :param period: The period in seconds
        :param whitelist: A list of IP addresses or CIDR ranges to exclude from rate limiting
        """
        self.request = request
        self.limit = limit
        self.period = period
        self.whitelist = whitelist
        self.github_ips_update_interval = github_ips_update_interval
        self.redis = redis
        self._script_sha = None

    def _ip_address(self) -> str:
        """
        Get the client's IP address from the request headers.
        """
        return ip_address(request=self.request)

    def _request_identifier(self) -> str:
        """
        Generate a unique identifier for the request based on the path and client IP address.
        """
        path_hash = md5(self.request.scope["path"].encode()).hexdigest()
        return f"rate_limiter:{self._ip_address()}:{path_hash}"

    async def _redis_script_sha(self):
        """
        Load the rate limiting Lua script into Redis and return its SHA hash.
        """
        if not self._script_sha:
            self._script_sha = await self.redis.script_load(rate_limit_lua_script)
        return self._script_sha

    async def _update_github_action_runners(self):
        """
        Aggregate all relevant GitHub CIDR sources and update the Redis set of GitHub IPs.
        """
        current_time = int(datetime.now().timestamp())
        last_update = int(
            (await self.redis.get(self._github_ips_last_update_key)) or "0"
        )
        if current_time - last_update < self.github_ips_update_interval:
            return
        async with httpx.AsyncClient() as http_client:
            logger.info("Updating GitHub action runners..")
            response = await http_client.get(
                "https://api.github.com/meta",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if response.status_code != 200:
                logger.error(f"Failed to update GitHub action runners: {response.text}")
                return
            data = response.json()
            github_ips = set()
            for key in ("actions", "hooks", "api"):
                values = data.get(key) or []
                if isinstance(values, list):
                    github_ips.update(v for v in values if isinstance(v, str))
            if not github_ips:
                logger.error("No GitHub IPs found, ignoring")
                return
            await self.redis.delete(self._github_ips_key)
            await self.redis.sadd(self._github_ips_key, *list(github_ips))
            await self.redis.set(self._github_ips_last_update_key, current_time)
            logger.info(f"GitHub IPs ({len(github_ips)}) updated")

    async def _is_whitelisted(self) -> bool:
        """
        Check if the client's IP address is in the whitelist.
        """
        request_path = self.request.scope["path"]
        if request_path not in whitelistable_paths:
            return False
        try:
            ip_address = ipaddress.ip_address(self._ip_address())
            await self._update_github_action_runners()
            for address in self.whitelist:
                try:
                    if ip_address in ipaddress.ip_network(address):
                        return True
                except ValueError:
                    continue
            for runner in await self.redis.smembers(self._github_ips_key):
                try:
                    if ip_address in ipaddress.ip_network(runner):
                        return True
                except ValueError:
                    continue
            return False
        except ValueError:
            return False

    async def is_allowed(
        self,
        key: str | None = None,
    ) -> tuple[bool, int]:
        """
        Check if the request is allowed based on the rate limit.
        This also increments the request count in Redis on each call.

        :return: A tuple containing a boolean indicating if the request is allowed
        and the time left (TTL in seconds) until the request is allowed again.
        """
        request_path = self.request.scope["path"]

        if request_path in private_paths:
            return (True, 0)
        if request_path in excluded_paths:
            return (True, 0)
        if await self._is_whitelisted():
            return (True, 0)
        key = key or self._request_identifier()
        try:
            script_sha = await self._redis_script_sha()
            time_left = await self.redis.evalsha(
                script_sha,
                1,
                key,
                str(self.limit),
                str(self.period),
            )
            return (time_left == 0, time_left)
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return (True, 0)

    async def is_allowed_manual(self, key: str | None = None) -> tuple[bool, int]:
        """
        Check if the request is allowed based on the rate limit.
        This also increments the request count in Redis on each call.

        :param key: The key to use for rate limiting. If None, the request path and client IP address will be used.
        """
        return await self.is_allowed(key=key)
