import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.launchpad.models import LaunchpadAccessTokenResponse, LaunchpadProfile
from app.launchpad.routes import (
    launchpad_callback,
    launchpad_login,
    launchpad_logout,
    launchpad_profile,
)


@pytest.mark.asyncio
async def test_login():
    launchpad_service = MagicMock()
    launchpad_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    response = await launchpad_login(
        redirect_url=base64.b64encode("https://example.com".encode()).decode("utf-8"),
        launchpad_service=launchpad_service,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert launchpad_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    launchpad_service = MagicMock()
    launchpad_service.callback = AsyncMock(
        return_value=LaunchpadAccessTokenResponse(
            oauth_token="test_oauth_token", oauth_token_secret="test_oauth_token_secret"
        )
    )
    launchpad_service.encrypt = MagicMock(return_value="test_encrypted_token")
    state = "test_state"
    request = Request(
        {"url": "http://test.com/callback", "type": "http", "router": "launchpad"}
    )
    launchpad_session = {
        "state": state,
        "success_redirect_url": "http://test.com/profile",
    }
    response = await launchpad_callback(
        request, state, launchpad_session, launchpad_service
    )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "http://test.com/profile?access_token=test_encrypted_token"
    )
    assert launchpad_service.callback.called


@pytest.mark.asyncio
async def test_callback_invalid_params():
    launchpad_service = MagicMock()
    launchpad_service.callback = AsyncMock(
        return_value=LaunchpadAccessTokenResponse(
            oauth_token="test_oauth_token", oauth_token_secret="test_oauth_token_secret"
        )
    )
    state = None
    request = Request(
        {"url": "http://test.com/callback", "type": "http", "router": "launchpad"}
    )
    launchpad_session = {"state": "test_state"}
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called

    state = "test_state"
    launchpad_session = None
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called

    state = "invalid_test_state"
    launchpad_session = {"state": "test_state"}
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called


@pytest.mark.asyncio
async def test_profile():
    launchpad_service = MagicMock()
    launchpad_service.profile = AsyncMock(
        return_value=LaunchpadProfile(
            emails=["email1", "email2"], _id="test_id", username="test_username"
        )
    )

    launchpad_session = {"state": "test_state"}
    response = await launchpad_profile(launchpad_session, launchpad_service)

    assert response.model_dump() == {
        "emails": ["email1", "email2"],
        "username": "test_username",
    }
    assert launchpad_service.profile.called

    launchpad_session = None
    launchpad_service.profile.reset_mock()
    with pytest.raises(HTTPException):
        await launchpad_profile(launchpad_session, launchpad_service)

    assert not launchpad_service.profile.called


@pytest.mark.asyncio
async def test_logout():
    response = await launchpad_logout()
    assert response.status_code == 200
