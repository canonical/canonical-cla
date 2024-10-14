import logging
from contextvars import ContextVar
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import PlainTextResponse

from app.config import config
from app.security.rate_limiter import RateLimiter
from app.utils import ip_address, is_local_request

logger = logging.getLogger(__name__)

allowed_origins = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "*.ubuntu.com",
    "*.canonical.com",
    "*.demos.haus",
]

private_paths = ["/_status/check", "/metrics"]


def is_url_match(url, patterns):
    # Remove protocol and path from the URL
    domain = url.split("://")[-1].split("/")[0]

    # Remove port if present
    domain = domain.split(":")[0]

    for pattern in patterns:
        if pattern.startswith("*"):
            if domain.endswith(pattern[1:]):
                return True
        elif domain == pattern:
            return True
    return False


request_ip_address_context_var: ContextVar[str] = ContextVar(
    "request_ip_address", default=None
)


def request_ip():
    return request_ip_address_context_var.get()


def register_middlewares(app: FastAPI):
    @app.middleware("http")
    async def flatten_query_string_lists(request: Request, call_next):
        """
        FastAPI has support for array query parameters. However only this format is supported:
        `/items?item=foo&item=bar`
        whereas the following format is not supported:
        `/items?item=foo,bar`
        This middleware converts the latter format to the former format.
        """
        flattened = []
        for key, value in request.query_params.multi_items():
            flattened.extend((key, entry) for entry in value.split(","))
        request.scope["query_string"] = urlencode(flattened, doseq=True).encode("utf-8")
        return await call_next(request)

    @app.middleware("http")
    async def query_handle_empty_value(request: Request, call_next):
        """
        FastAPI raises a JSONDecodeError error with status code 500 when a query parameter is empty.
        The unsupported format is `/items?item=`.
        This middleware converts the unsupported format to `/items`.
        """
        cleaned = []
        for key, value in request.query_params.items():
            if value:
                cleaned.append((key, value))

        request.scope["query_string"] = urlencode(cleaned).encode("utf-8")
        return await call_next(request)

    @app.middleware("http")
    async def strict_cors_middleware(request: Request, call_next):
        origin = request.headers.get("Origin")
        headers = {}
        if origin and is_url_match(origin, allowed_origins):
            headers["Access-Control-Allow-Origin"] = origin
        else:  # Allow all origins, which will not allow to include credentials
            headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type"
        if request.method == "OPTIONS":
            return PlainTextResponse("OK", status_code=200, headers=headers)
        else:
            response = await call_next(request)
            for key, value in headers.items():
                response.headers[key] = value

        return response

    @app.middleware("http")
    async def no_cache_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        response.headers["Expires"] = "0"
        return response

    @app.middleware("http")
    async def set_client_ip(request: Request, call_next):
        client_ip = ip_address(request)
        request.scope["client"] = (client_ip, request.scope["client"][1])
        context_token = request_ip_address_context_var.set(client_ip)
        response = await call_next(request)
        request_ip_address_context_var.reset(context_token)
        return response

    @app.middleware("http")
    async def protect_private_paths(request: Request, call_next):
        if request.url.path in private_paths and not is_local_request(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        else:
            return await call_next(request)

    @app.middleware("http")
    async def rate_limit_middleware(
        request: Request,
        call_next,
    ):
        """
        Rate limiting middleware for FastAPI.
        """
        limiter = RateLimiter(
            request,
            limit=config.rate_limit.limit,
            period=config.rate_limit.period,
            whitelist=config.rate_limit.whitelist,
        )
        # attach the limiter to the request object
        request.state.rate_limit = limiter
        allowed, time_left = await limiter.is_allowed()
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"message": "Too many requests"},
                headers={"Retry-After": str(time_left)},
            )
        return await call_next(request)

    def on_app_ready_callback():
        logger.info(
            "CORS middleware is enabled with allowed origins %s",
            allowed_origins,
        )
        logger.info(
            f"Rate limiting is enabled with limit {config.rate_limit.limit} requests per {config.rate_limit.period} seconds and whitelist %s",
            config.rate_limit.whitelist,
        )

    return on_app_ready_callback
