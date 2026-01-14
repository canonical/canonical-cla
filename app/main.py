import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator as PrometheusInstrumentator
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.cla.routes import cla_router
from app.config import config
from app.docs import get_redoc_html
from app.github.routes import github_router
from app.launchpad.routes import launchpad_router
from app.logging import configure_logger
from app.middlewares import register_middlewares
from app.oidc.routes import oidc_router
from app.security.config import private_paths

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logger()
    on_app_ready_callback()
    yield


if config.sentry_dsn:
    logger.info("Sentry is enabled")
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        environment=config.environment,
        debug=config.debug_mode,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            HttpxIntegration(),
            AsyncPGIntegration(),
        ],
        # Sample traces for all paths except private paths
        traces_sampler=lambda sampling_context: (
            1.0
            if sampling_context.get("asgi_scope", {}).get("path")
            not in list(private_paths)
            else 0.0
        ),
    )

app = FastAPI(
    title=config.app_name,
    version="1.0.0-alpha",
    debug=config.debug_mode,
    lifespan=lifespan,
    redoc_url=None,
    docs_url=None,
)

PrometheusInstrumentator(excluded_handlers=list(private_paths)).instrument(app).expose(
    app
)

on_app_ready_callback = register_middlewares(app)

app.include_router(cla_router)
app.include_router(github_router)
app.include_router(launchpad_router)
app.include_router(oidc_router)


@app.get("/", include_in_schema=False)
def read_root(request: Request):
    return {
        "message": "Welcome to Canonical Contribution Licence Agreement (CLA) Service",
        "docs": request.url_for("redoc_html")._url,
    }


@app.get("/debug-ip", include_in_schema=False)
def debug_ip(request: Request):
    return {"client_ip": request.client.host}


@app.get("/docs", include_in_schema=False)
async def redoc_html():
    state = app.state._state
    if state.get("redoc_html") is None:
        state["redoc_html"] = get_redoc_html()

    return state["redoc_html"]


@app.get("/_status/check", include_in_schema=False)
def health_check():
    return {"status": "OK"}
