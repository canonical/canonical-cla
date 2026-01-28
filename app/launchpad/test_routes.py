from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.launchpad.models import LaunchpadProfile, RequestTokenSession
from app.launchpad.routes import (
    launchpad_callback,
    launchpad_login,
    launchpad_logout,
    launchpad_profile,
)
from app.utils.base64 import Base64


@pytest.mark.asyncio
async def test_login():
    launchpad_service = MagicMock()
    launchpad_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    response = await launchpad_login(
        redirect_url=Base64.encode("https://example.com"),
        launchpad_service=launchpad_service,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert launchpad_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    launchpad_service = MagicMock()
    launchpad_service.callback = AsyncMock(
        return_value=RedirectResponse(url="http://test.com/profile")
    )
    state = "test_state"
    launchpad_session = RequestTokenSession(
        oauth_token="test_oauth_token",
        oauth_token_secret="test_oauth_token_secret",
        state=state,
        redirect_url="http://test.com/profile",
    )
    response = await launchpad_callback(
        state=state,
        launchpad_session=launchpad_session,
        launchpad_service=launchpad_service,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com/profile"
    assert launchpad_service.callback.called


@pytest.mark.asyncio
async def test_callback_missing_session():
    launchpad_service = MagicMock()
    state = "test_state"
    with pytest.raises(HTTPException) as exc_info:
        await launchpad_callback(
            state=state,
            launchpad_session=None,
            launchpad_service=launchpad_service,
        )
    assert exc_info.value.status_code == 401
    assert not launchpad_service.callback.called


@pytest.mark.asyncio
async def test_callback_state_mismatch():
    launchpad_service = MagicMock()
    state = "test_state"
    launchpad_session = RequestTokenSession(
        oauth_token="test_oauth_token",
        oauth_token_secret="test_oauth_token_secret",
        state="different_state",
        redirect_url="http://test.com/profile",
    )
    with pytest.raises(HTTPException) as exc_info:
        await launchpad_callback(
            state=state,
            launchpad_session=launchpad_session,
            launchpad_service=launchpad_service,
        )
    assert exc_info.value.status_code == 401
    assert not launchpad_service.callback.called


@pytest.mark.asyncio
async def test_profile_success():
    launchpad_user = LaunchpadProfile(
        emails=["email1", "email2"], _id="test_id", username="test_username"
    )
    response = await launchpad_profile(launchpad_user=launchpad_user)
    assert response == launchpad_user


@pytest.mark.asyncio
async def test_logout():
    launchpad_service = MagicMock()
    launchpad_service.logout = MagicMock(return_value=RedirectResponse(url="http://t"))
    response = await launchpad_logout(
        redirect_url=None,
        launchpad_service=launchpad_service,
    )
    assert response.status_code == 307
    launchpad_service.logout.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_logout_with_redirect():
    launchpad_service = MagicMock()
    redirect_url = Base64.encode("http://test.com/logout")
    launchpad_service.logout = MagicMock(
        return_value=RedirectResponse(url="http://test.com/logout")
    )
    response = await launchpad_logout(
        redirect_url=redirect_url,
        launchpad_service=launchpad_service,
    )
    assert response.status_code == 307
    launchpad_service.logout.assert_called_once_with(Base64.decode_str(redirect_url))
