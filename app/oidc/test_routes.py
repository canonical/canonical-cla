import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.oidc.models import OIDCProfile
from app.oidc.routes import oidc_callback, oidc_login, oidc_logout, oidc_profile


@pytest.mark.asyncio
async def test_login():
    oidc_service = MagicMock()
    oidc_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login.canonical.com/authorize")
    )

    response = await oidc_login(
        redirect_url=base64.b64encode(b"https://example.com/dashboard").decode(),
        oidc_service=oidc_service,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://login.canonical.com/authorize"
    assert oidc_service.login.called


@pytest.mark.asyncio
async def test_login_without_redirect():
    oidc_service = MagicMock()
    oidc_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login.canonical.com/authorize")
    )

    response = await oidc_login(redirect_url=None, oidc_service=oidc_service)

    assert response.status_code == 307
    oidc_service.login.assert_called_once()
    call_kwargs = oidc_service.login.call_args.kwargs
    assert call_kwargs["redirect_url"] is None


@pytest.mark.asyncio
async def test_callback_success():
    oidc_service = MagicMock()
    oidc_service.callback = AsyncMock(return_value="test_access_token")
    oidc_service.encrypt = MagicMock(return_value="encrypted_token")

    oidc_session = {"state": "test_state", "redirect_url": "http://test.com/dashboard"}

    response = await oidc_callback(
        code="test_code",
        state="test_state",
        error_description=None,
        oidc_session=oidc_session,
        oidc_service=oidc_service,
    )

    assert response.status_code == 307
    assert "access_token=encrypted_token" in response.headers["location"]
    assert oidc_service.callback.called


@pytest.mark.asyncio
async def test_callback_missing_session():
    oidc_service = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="test_code",
            state="test_state",
            error_description=None,
            oidc_session=None,
            oidc_service=oidc_service,
        )

    assert exc.value.status_code == 401
    assert "session missing" in exc.value.detail


@pytest.mark.asyncio
async def test_callback_missing_code():
    oidc_service = MagicMock()
    oidc_session = {"state": "test_state"}

    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code=None,
            state="test_state",
            error_description=None,
            oidc_session=oidc_session,
            oidc_service=oidc_service,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_callback_state_mismatch():
    oidc_service = MagicMock()
    oidc_session = {"state": "correct_state"}

    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="test_code",
            state="wrong_state",
            error_description=None,
            oidc_session=oidc_session,
            oidc_service=oidc_service,
        )

    assert exc.value.status_code == 401
    assert "state mismatch" in exc.value.detail


@pytest.mark.asyncio
async def test_callback_error_with_redirect():
    oidc_service = MagicMock()
    oidc_session = {"state": "test_state", "redirect_url": "http://test.com/dashboard"}

    response = await oidc_callback(
        code="test_code",
        state="test_state",
        error_description="access_denied",
        oidc_session=oidc_session,
        oidc_service=oidc_service,
    )

    assert response.status_code == 307
    assert "oidc_error=access_denied" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_error_without_redirect():
    oidc_service = MagicMock()
    oidc_session = {"state": "test_state", "redirect_url": None}

    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="test_code",
            state="test_state",
            error_description="access_denied",
            oidc_session=oidc_session,
            oidc_service=oidc_service,
        )

    assert exc.value.status_code == 400
    assert "access_denied" in exc.value.detail


@pytest.mark.asyncio
async def test_callback_service_error_with_redirect():
    oidc_service = MagicMock()
    oidc_service.callback = AsyncMock(
        side_effect=HTTPException(status_code=400, detail="Token exchange failed")
    )
    oidc_session = {"state": "test_state", "redirect_url": "http://test.com/dashboard"}

    response = await oidc_callback(
        code="test_code",
        state="test_state",
        error_description=None,
        oidc_session=oidc_session,
        oidc_service=oidc_service,
    )

    assert response.status_code == 307
    assert "oidc_error" in response.headers["location"]


@pytest.mark.asyncio
async def test_profile_success():
    mock_profile = OIDCProfile(
        sub="user123",
        email="user@canonical.com",
        email_verified=True,
        name="Test User",
        username="testuser",
    )
    oidc_service = MagicMock()
    oidc_service.profile = AsyncMock(return_value=mock_profile)

    response = await oidc_profile(
        access_token="test_access_token",
        oidc_service=oidc_service,
    )

    assert response == mock_profile
    oidc_service.profile.assert_called_once_with("test_access_token")


@pytest.mark.asyncio
async def test_profile_missing_token():
    oidc_service = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await oidc_profile(access_token=None, oidc_service=oidc_service)

    assert exc.value.status_code == 401
    assert "access token missing" in exc.value.detail
    assert not oidc_service.profile.called


@pytest.mark.asyncio
async def test_logout_with_redirect():
    redirect_url = base64.b64encode(b"https://example.com").decode()

    response = await oidc_logout(redirect_url=redirect_url)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_logout_without_redirect():
    response = await oidc_logout(redirect_url=None)

    assert response.status_code == 200
