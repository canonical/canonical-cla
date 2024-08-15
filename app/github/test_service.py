import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.github.models import GitHubAccessTokenResponse, GithubPendingAuthSession
from app.github.service import GithubService


@patch("secrets.token_urlsafe", return_value="test_state")
@patch("app.config.config.github_oauth.client_id", "test_client_id")
@pytest.mark.asyncio
async def test_login_success(token_urlsafe):
    cookie_session = MagicMock()
    http_client = MagicMock()
    github_service = GithubService(cookie_session, http_client)
    response = await github_service.login("http://test.com")
    assert cookie_session.set_cookie.called
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://github.com/login")
    assert "test_state" in response.headers["location"]
    assert "test_client_id" in response.headers["location"]
    assert "test.com" in response.headers["location"]


@patch("app.config.config.github_oauth.client_id", "test_client_id")
@patch(
    "app.config.config.github_oauth.client_secret.get_secret_value",
    lambda: "test_client_secret",
)
@pytest.mark.asyncio
async def test_callback_success():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json=GitHubAccessTokenResponse(
                access_token="test_access_token",
                token_type="bearer",
                scope="user",
            ),
        )
    )
    github_service = GithubService(cookie_session, http_client)
    response = await github_service.callback("test_code", "http://test.com")
    assert cookie_session.set_cookie.called
    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com"


@pytest.mark.asyncio
async def test_callback_bad_request():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=400,
            json={"error": "bad_request", "error_description": "Bad Request"},
        )
    )
    github_service = GithubService(cookie_session, http_client)
    with pytest.raises(HTTPException):
        await github_service.callback("test_code", "http://test.com")

    assert cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_emails_success():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json=[
                {"email": "email1", "verified": True},
                {"email": "email2", "verified": False},
                {"email": "email3", "verified": True},
            ],
        )
    )
    github_service = GithubService(cookie_session, http_client)
    response = await github_service.emails("test_access_token")
    assert response == ["email1", "email3"]
    assert cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_emails_failure():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=httpx.Response(status_code=500))
    github_service = GithubService(cookie_session, http_client)
    with pytest.raises(HTTPException):
        await github_service.emails("test_access_token")
    assert cookie_session.set_cookie.called is False
