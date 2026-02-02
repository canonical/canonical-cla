from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request

from app.security.rate_limiter import RateLimiter


def build_request(path: str, headers: dict[str, str] | None = None) -> Request:
    headers = headers or {}
    header_items = [
        (key.encode("latin-1"), value.encode("latin-1"))
        for key, value in headers.items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": header_items,
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_excluded_path_is_allowed():
    request = build_request("/_status/check")
    redis = AsyncMock()

    limiter = RateLimiter(
        request=request,
        limit=10,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed, time_left = await limiter.is_allowed()

    assert allowed is True
    assert time_left == 0
    redis.evalsha.assert_not_called()


@pytest.mark.asyncio
async def test_whitelisted_ip_on_whitelistable_path_bypasses_limit():
    # Path must match exactly the whitelistable path value (no leading slash)
    request = build_request(
        "/cla/check",
        headers={"x-forwarded-for": "1.2.3.4"},
    )
    redis = AsyncMock()
    redis.get.return_value = "0"
    redis.smembers.return_value = []

    # Avoid network calls in sandbox by skipping GitHub meta refresh.
    with patch.object(RateLimiter, "_update_github_action_runners", new=AsyncMock()):
        limiter = RateLimiter(
            request=request,
            limit=1,
            period=60,
            whitelist=["1.2.3.0/24"],
            redis=redis,
        )

        allowed, time_left = await limiter.is_allowed()

    assert allowed is True
    assert time_left == 0
    redis.evalsha.assert_not_called()


@pytest.mark.asyncio
async def test_github_runner_ip_is_whitelisted_after_meta_update():
    # IP falls within returned GitHub Actions CIDR
    request = build_request(
        "/cla/check",
        headers={"x-forwarded-for": "20.207.73.10"},
    )
    redis = AsyncMock()
    # Force update (last_update == 0)
    redis.get.return_value = "0"
    # After update, smembers should return the runners we added
    redis.smembers.return_value = ["20.207.73.0/25", "21.207.73.0/25", "1.2.3.4"]

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "actions": ["20.207.73.0/25"],
                "hooks": ["21.207.73.0/25"],
                "api": ["1.2.3.4"],
            }

        @property
        def text(self):
            return "ok"

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return FakeResponse()

    with patch(
        "app.security.rate_limiter.httpx.AsyncClient", return_value=FakeAsyncClient()
    ):
        limiter = RateLimiter(
            request=request,
            limit=1,
            period=60,
            whitelist=[],
            github_ips_update_interval=0,
            redis=redis,
        )

        allowed, time_left = await limiter.is_allowed()

        assert allowed is True
        assert time_left == 0
        redis.delete.assert_awaited()
        redis.sadd.assert_awaited()
        # Ensure CIDRs from actions, hooks and api were added to Redis
        sadd_call = redis.sadd.await_args
        sadd_args = getattr(sadd_call, "args", ())
        assert sadd_args[0] == limiter._github_ips_key
        added = set(sadd_args[1:])
        assert added == {"20.207.73.0/25", "21.207.73.0/25", "1.2.3.4"}
        redis.set.assert_awaited()
        redis.evalsha.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_allows_then_blocks_using_manual_key():
    request = build_request("/api")
    redis = AsyncMock()
    redis.script_load.return_value = "sha-1"
    # Two allowed (0), then blocked with 1500 ms left
    redis.evalsha.side_effect = [0, 0, 1500]

    limiter = RateLimiter(
        request=request,
        limit=2,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed1, t1 = await limiter.is_allowed_manual(key="user:1")
    allowed2, t2 = await limiter.is_allowed_manual(key="user:1")
    allowed3, t3 = await limiter.is_allowed_manual(key="user:1")

    assert (allowed1, t1) == (True, 0)
    assert (allowed2, t2) == (True, 0)
    assert (allowed3, t3) == (False, 1500)


@pytest.mark.asyncio
async def test_is_allowed_handles_redis_error():
    request = build_request("/api", headers={"x-forwarded-for": "8.8.8.8"})
    redis = AsyncMock()
    redis.script_load.return_value = "sha-1"
    redis.evalsha.side_effect = RuntimeError("boom")

    limiter = RateLimiter(
        request=request,
        limit=1,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed, time_left = await limiter.is_allowed_manual(key="k")

    assert allowed is True
    assert time_left == 0


@pytest.mark.asyncio
async def test_private_path_bypasses_rate_limit():
    request = build_request("/metrics")
    redis = AsyncMock()

    limiter = RateLimiter(
        request=request,
        limit=10,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed, time_left = await limiter.is_allowed()

    assert allowed is True
    assert time_left == 0
    # Ensure Redis was not touched for rate limiting
    redis.evalsha.assert_not_called()
    redis.script_load.assert_not_called()


@pytest.mark.asyncio
async def test_excluded_path_bypasses_rate_limit():
    request = build_request("/docs")
    redis = AsyncMock()

    limiter = RateLimiter(
        request=request,
        limit=10,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed, time_left = await limiter.is_allowed()

    assert allowed is True
    assert time_left == 0
    # Ensure Redis was not touched for rate limiting
    redis.evalsha.assert_not_called()
    redis.script_load.assert_not_called()


@pytest.mark.asyncio
async def test_standard_path_enforces_rate_limit():
    request = build_request("/api/resource")
    redis = AsyncMock()
    redis.script_load.return_value = "mock_sha"
    # Return 0 means allowed (count incremented)
    redis.evalsha.return_value = 0

    limiter = RateLimiter(
        request=request,
        limit=5,
        period=60,
        whitelist=[],
        redis=redis,
    )

    allowed, time_left = await limiter.is_allowed()

    assert allowed is True
    assert time_left == 0

    redis.script_load.assert_awaited_once()
    redis.evalsha.assert_awaited_once_with(
        "mock_sha",
        1,
        limiter._request_identifier(),
        "5",
        "60",
    )
