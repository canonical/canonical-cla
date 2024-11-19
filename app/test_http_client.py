from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from httpx import Response

from app.http_client import HTTPClient


@pytest.fixture
def mock_request(mocker):
    response = AsyncMock()
    mocker.patch("httpx.AsyncClient.request", response)
    return response


@pytest.mark.asyncio
async def test_success_request(mock_request):
    mock_request.return_value = Response(status_code=200, content=b"success")
    http_client = HTTPClient()
    response = await http_client.request("GET", "http://example.com")
    assert response.status_code == 200
    assert response.content == b"success"


@pytest.mark.asyncio
async def test_failed_request(mock_request):
    mock_request.side_effect = httpx.TimeoutException(message="Timeout")
    http_client = HTTPClient()
    with pytest.raises(HTTPException) as e:
        await http_client.get("http://example.com")

    assert e.value.status_code == 500
    assert e.value.detail == "Failed to connect to example.com, please try again later"
