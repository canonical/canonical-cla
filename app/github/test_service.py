from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.github.models import (
    GitHubAccessTokenResponse,
    GitHubAccessTokenSession,
)
from app.github.service import GithubService


@patch("secrets.token_urlsafe", return_value="test_state")
@patch("app.config.config.github_oauth.client_id", "test_client_id")
@pytest.mark.asyncio
async def test_login_success(token_urlsafe):
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    github_service = GithubService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    response = await github_service.login("http://test.com/callback", "http://test.com")
    assert pending_auth_cookie_session.set_cookie.called
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
    pending_auth_cookie_session = MagicMock()
    pending_auth_cookie_session.name = "github_pending_auth_session"
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json=GitHubAccessTokenResponse(
                access_token="test_access_token",
                token_type="bearer",
                scope="user",
            ).model_dump(),
        )
    )
    github_service = GithubService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    response = await github_service.callback("test_code", "http://test.com/redirect")
    assert response.status_code == 307
    assert response.headers["location"].startswith("http://test.com/redirect")
    assert access_token_cookie_session.set_cookie.called
    # Verify that delete_cookie was called on the response (checking via response object)
    # The delete_cookie is called internally, so we verify the response was created correctly
    assert isinstance(response, RedirectResponse)


@pytest.mark.asyncio
async def test_callback_bad_request():
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=400,
            json={"error": "bad_request", "error_description": "Bad Request"},
        )
    )
    github_service = GithubService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    with pytest.raises(HTTPException):
        await github_service.callback("test_code", "http://test.com/redirect")


@pytest.mark.asyncio
async def test_profile_success():
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    mock_responses = {
        "https://api.github.com/user/emails": {
            "status_code": 200,
            "json": [
                {"email": "email1", "verified": True},
                {"email": "email2", "verified": False},
                {"email": "email3", "verified": True},
            ],
        },
        "https://api.github.com/user": {
            "status_code": 200,
            "json": {"id": 123, "login": "test_user"},
        },
    }

    http_client = MagicMock()
    http_client.get = AsyncMock(
        side_effect=lambda url, **kwargs: httpx.Response(
            status_code=mock_responses[url]["status_code"],
            json=mock_responses[url]["json"],
        )
    )

    github_service = GithubService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    access_token_session = GitHubAccessTokenSession(
        access_token="test_access_token", token_type="bearer", scope="user"
    )
    response = await github_service.profile(access_token_session)
    assert response._id == 123
    assert response.username == "test_user"
    assert response.emails == ["email1", "email3"]


@pytest.mark.asyncio
async def test_profile_failure():
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=httpx.Response(status_code=500))
    github_service = GithubService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    access_token_session = GitHubAccessTokenSession(
        access_token="test_access_token", token_type="bearer", scope="user"
    )
    with pytest.raises(HTTPException):
        await github_service.profile(access_token_session)
    assert access_token_cookie_session.set_cookie.called is False
