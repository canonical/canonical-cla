import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL

from app.github.routes import (
    github_callback,
    github_login,
    github_logout,
    github_profile,
)


@pytest.mark.asyncio
async def test_login():
    github_service = MagicMock()
    github_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: URL("http://test.com/callback")
    response = await github_login(
        request,
        base64.b64encode("https://example.com".encode()).decode("utf-8"),
        github_service,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert github_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    github_service = MagicMock()
    github_service.callback = AsyncMock(return_value="secret_token")
    github_service.encrypt = MagicMock(return_value="test_encrypted_token")
    code = "test_code"
    state = "test_state"
    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    github_session = {"state": state, "success_redirect_url": "http://test.com/profile"}
    response = await github_callback(
        request,
        code=code,
        state=state,
        github_session=github_session,
        github_service=github_service,
    )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "http://test.com/profile?access_token=test_encrypted_token"
    )
    assert github_service.callback.called


@pytest.mark.asyncio
async def test_profile_success():
    github_service = MagicMock()
    github_service.profile = AsyncMock(return_value=["email1", "email2"])
    github_session = {"access_token": "test_access_token"}
    response = await github_profile(github_session, github_service)
    assert response == ["email1", "email2"]
    assert github_service.profile.called

    github_service.reset_mock()
    github_service.profile.reset_mock()
    github_session = None
    with pytest.raises(HTTPException):
        await github_profile(github_session, github_service)

    assert not github_service.profile.called


@pytest.mark.asyncio
async def test_logout():
    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: URL("http://test.com/login")
    response = await github_logout(request)

    assert response.status_code == 200
