import os
from typing import Any, AsyncIterator

import httpx
from fastapi import HTTPException

from app.config import config


class HTTPClient(httpx.AsyncClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        retry_config: dict[str, Any] = {"retries": config.http_max_retries}

        mounts: dict[str, httpx.AsyncHTTPTransport] = {}
        http_proxy: str | None = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy: str | None = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        if http_proxy:
            mounts["http://"] = httpx.AsyncHTTPTransport(
                proxy=http_proxy, **retry_config
            )
        else:
            mounts["http://"] = httpx.AsyncHTTPTransport(**retry_config)
        if https_proxy:
            mounts["https://"] = httpx.AsyncHTTPTransport(
                proxy=https_proxy, **retry_config
            )
        else:
            mounts["https://"] = httpx.AsyncHTTPTransport(**retry_config)

        kwargs.setdefault("mounts", mounts)
        kwargs.setdefault("timeout", config.http_timeout)
        kwargs.setdefault("follow_redirects", True)

        super().__init__(*args, **kwargs)

    async def request(
        self,
        method: str,
        url: str | httpx.URL,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            return await super().request(method, url, *args, **kwargs)
        except httpx.HTTPError as exc:
            url_obj = httpx.URL(url)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to {url_obj.host}, please try again later",
            ) from exc


async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with HTTPClient() as client:
        yield client
