import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app.cla.routes import cla_router
from app.config import config
from app.docs import get_redoc_html
from app.github.routes import github_router
from app.launchpad.routes import launchpad_router
from app.logging import setup_logging
from app.middlewares import register_middlewares


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    on_app_ready_callback()
    yield


app = FastAPI(
    title=config.app_name,
    version="1.0.0-alpha",
    debug=config.debug_mode,
    lifespan=lifespan,
    redoc_url=None,
    docs_url=None,
)
on_app_ready_callback = register_middlewares(app)
Instrumentator().instrument(app).expose(app)
app.include_router(cla_router)
app.include_router(github_router)
app.include_router(launchpad_router)


@app.get("/", include_in_schema=False)
def read_root(request: Request):
    return {
        "message": "Welcome to Canonical Contribution Licence Agreement (CLA) Service",
        "docs": request.url_for("redoc_html")._url,
    }


@app.get("/debug-ip", include_in_schema=False)
def debug_ip(request: Request):
    return {"client_ip": request.client.host}


@app.get("/debug-error", include_in_schema=False)
def debug_error():
    1 / 0


@app.get("/docs", include_in_schema=False)
async def redoc_html():
    state = app.state._state
    if state.get("redoc_html") is None:
        state["redoc_html"] = get_redoc_html()

    return state["redoc_html"]


@app.get("/_status/check", include_in_schema=False)
def health_check():
    return {"status": "OK"}
