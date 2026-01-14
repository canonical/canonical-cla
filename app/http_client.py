from typing import Any

import httpx
from fastapi import HTTPException

from app.config import config


class HTTPClient(httpx.AsyncClient):
    client: httpx.AsyncClient = None

    async def request(
        self,
        method: str,
        url: httpx._types.URLTypes,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        if not self.client:
            transport = httpx.AsyncHTTPTransport(retries=config.http_max_retries)
            self.client = httpx.AsyncClient(
                transport=transport, timeout=config.http_timeout, follow_redirects=True
            )
        try:
            return await self.client.request(method, url, *args, **kwargs)
        except httpx.HTTPError as err:
            host = httpx._urls.URL(url).host
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to {host}, please try again later",
            ) from err
