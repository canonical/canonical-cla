from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.cla.routes import cla_router
from app.config import config
from app.docs import get_redoc_html
from app.github.routes import github_router
from app.launchpad.routes import launchpad_router
from app.logging import setup_logging
from app.middlewares import register_middlewares


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
app.include_router(cla_router)
app.include_router(github_router)
app.include_router(launchpad_router)


@app.get("/", include_in_schema=False)
def read_root(request: Request):
    return {
        "message": "Welcome to Canonical Contribution Licence Agreement (CLA) Service",
        "docs": request.url_for("redoc_html")._url,
    }


@app.get("/docs", include_in_schema=False)
async def redoc_html():
    state = app.state._state
    if state.get("redoc_html") is None:
        state["redoc_html"] = get_redoc_html()

    return state["redoc_html"]


@app.get("/healthz", include_in_schema=False)
def health_check():
    return {"status": "OK"}


# @app.get("/test-redis")
# async def test_redis():
#     await redis.set("test-key", "test-value")
#     return {"value": await redis.get("test-key")}


# DB testing routes wil be removed after testing
