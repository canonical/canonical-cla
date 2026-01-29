from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.github.models import (
    GithubPendingAuthSession,
    GitHubProfile,
)
from app.github.routes import (
    github_callback,
    github_login,
    github_logout,
    github_profile,
)
from app.utils.base64 import Base64


@pytest.mark.asyncio
async def test_login():
    github_service = MagicMock()
    github_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    redirect_url = Base64.encode("https://example.com")
    response = await github_login(
        redirect_url=redirect_url,
        github_service=github_service,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert github_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    github_service = MagicMock()
    redirect_response = RedirectResponse(url="http://test.com/profile")
    github_service.callback = AsyncMock(return_value=redirect_response)
    code = "test_code"
    state = "test_state"
    github_pending_auth_session = GithubPendingAuthSession(
        state=state, redirect_url="http://test.com/profile"
    )
    response = await github_callback(
        code=code,
        state=state,
        github_pending_auth_session=github_pending_auth_session,
        github_service=github_service,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com/profile"
    assert github_service.callback.called


@pytest.mark.asyncio
async def test_callback_missing_session():
    github_service = MagicMock()
    code = "test_code"
    state = "test_state"
    with pytest.raises(HTTPException) as exc_info:
        await github_callback(
            code=code,
            state=state,
            github_pending_auth_session=None,
            github_service=github_service,
        )
    assert exc_info.value.status_code == 401
    assert not github_service.callback.called


@pytest.mark.asyncio
async def test_callback_state_mismatch():
    github_service = MagicMock()
    code = "test_code"
    state = "test_state"
    github_pending_auth_session = GithubPendingAuthSession(
        state="different_state", redirect_url="http://test.com/profile"
    )
    with pytest.raises(HTTPException) as exc_info:
        await github_callback(
            code=code,
            state=state,
            github_pending_auth_session=github_pending_auth_session,
            github_service=github_service,
        )
    assert exc_info.value.status_code == 401
    assert not github_service.callback.called


@pytest.mark.asyncio
async def test_profile_success():
    github_user = GitHubProfile(
        _id=123, username="test_user", emails=["email1", "email2"]
    )
    response = await github_profile(github_user=github_user)
    assert response == github_user


@pytest.mark.asyncio
async def test_logout():
    github_service = MagicMock()
    github_service.logout = MagicMock(
        return_value=RedirectResponse(url="http://test.com")
    )
    response = await github_logout(
        redirect_url=None,
        github_service=github_service,
    )
    assert response.status_code == 307
    assert github_service.logout.called


@pytest.mark.asyncio
async def test_logout_with_redirect():
    github_service = MagicMock()
    redirect_url = Base64.encode("http://test.com/logout")
    github_service.logout = MagicMock(
        return_value=RedirectResponse(url="http://test.com/logout")
    )
    response = await github_logout(
        redirect_url=redirect_url,
        github_service=github_service,
    )
    assert response.status_code == 307
    assert github_service.logout.called
