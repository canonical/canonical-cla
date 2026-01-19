from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from app.oidc.models import (
    OIDCPendingAuthSession,
    OIDCUserInfo,
)
from app.oidc.service import OIDCService


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def mock_access_token_cookie_session():
    mock = MagicMock()
    mock.name = "access_token_session"
    return mock


@pytest.fixture
def mock_pending_auth_cookie_session():
    mock = MagicMock()
    mock.name = "pending_auth_session"
    return mock


@pytest.fixture
def oidc_service(
    mock_access_token_cookie_session, mock_pending_auth_cookie_session, mock_http_client
):
    service = OIDCService(
        access_token_cookie_session=mock_access_token_cookie_session,
        pending_auth_cookie_session=mock_pending_auth_cookie_session,
        http_client=mock_http_client,
    )
    return service


@pytest.fixture
def mock_metadata():
    return {
        "issuer": "https://login.canonical.com",
        "authorization_endpoint": "https://login.canonical.com/authorize",
        "token_endpoint": "https://login.canonical.com/token",
        "userinfo_endpoint": "https://login.canonical.com/userinfo",
        "jwks_uri": "https://login.canonical.com/jwks",
    }


@pytest.mark.asyncio
async def test_get_metadata_success(oidc_service, mock_http_client, mock_metadata):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )

    metadata = await oidc_service._get_metadata()

    assert metadata.issuer == mock_metadata["issuer"]
    mock_http_client.get.assert_called_once()

    # Test caching
    await oidc_service._get_metadata()
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_metadata_failure(oidc_service, mock_http_client):
    mock_http_client.get.return_value = MagicMock(status_code=500)

    with pytest.raises(HTTPException) as exc:
        await oidc_service._get_metadata()
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_get_metadata_validation_error(oidc_service, mock_http_client):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: {"invalid": "data"}
    )

    with pytest.raises(HTTPException) as exc:
        await oidc_service._get_metadata()
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_login(
    oidc_service, mock_http_client, mock_metadata, mock_pending_auth_cookie_session
):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )

    callback_url = "http://localhost/callback"
    redirect_uri = "/dashboard"

    response = await oidc_service.login(callback_url, redirect_uri)

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"].startswith(
        mock_metadata["authorization_endpoint"]
    )

    mock_pending_auth_cookie_session.set_cookie.assert_called_once()
    _, kwargs = mock_pending_auth_cookie_session.set_cookie.call_args
    assert isinstance(kwargs["value"], OIDCPendingAuthSession)
    assert kwargs["value"].redirect_uri == redirect_uri


@pytest.mark.asyncio
async def test_login_invalid_redirect_uri(oidc_service):
    callback_url = "http://localhost/callback"

    # Test launchpad/login
    with pytest.raises(HTTPException) as exc:
        await oidc_service.login(callback_url, "launchpad/login")
    assert exc.value.status_code == 400
    assert exc.value.detail.startswith("Invalid redirect_uri")

    # Test github/login
    with pytest.raises(HTTPException) as exc:
        await oidc_service.login(callback_url, "github/login")
    assert exc.value.status_code == 400
    assert exc.value.detail.startswith("Invalid redirect_uri")

    # Test paths ending with blocked paths
    with pytest.raises(HTTPException) as exc:
        await oidc_service.login(callback_url, "/some/path/launchpad/login")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        await oidc_service.login(callback_url, "/some/path/github/login")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_callback_success(
    oidc_service, mock_http_client, mock_metadata, mock_access_token_cookie_session
):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )

    token_response = {"access_token": "valid_token", "token_type": "Bearer"}
    mock_http_client.post.return_value = MagicMock(
        status_code=200, json=lambda: token_response
    )

    response = await oidc_service.callback("code", "callback_url", "/dashboard")

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/dashboard"

    mock_access_token_cookie_session.set_cookie.assert_called_once()


@pytest.mark.asyncio
async def test_callback_token_http_error(oidc_service, mock_http_client, mock_metadata):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )
    mock_http_client.post.return_value = MagicMock(status_code=400, text="Bad Request")

    with pytest.raises(HTTPException) as exc:
        await oidc_service.callback("code", "callback_url", "/dashboard")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_callback_token_response_error(
    oidc_service, mock_http_client, mock_metadata
):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"error": "invalid_grant", "error_description": "Bad code"},
    )

    with pytest.raises(HTTPException) as exc:
        await oidc_service.callback("code", "callback_url", "/dashboard")
    assert exc.value.status_code == 400
    assert "Bad code" in exc.value.detail


@pytest.mark.asyncio
async def test_callback_token_validation_error(
    oidc_service, mock_http_client, mock_metadata
):
    mock_http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: mock_metadata
    )
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "valid"},  # Missing token_type
    )

    with pytest.raises(HTTPException) as exc:
        await oidc_service.callback("code", "callback_url", "/dashboard")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_profile_success(oidc_service, mock_http_client, mock_metadata):
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_metadata),
        MagicMock(
            status_code=200,
            json=lambda: {"sub": "123", "name": "Test User", "email_verified": True},
        ),
    ]

    profile = await oidc_service.profile("token")

    assert isinstance(profile, OIDCUserInfo)
    assert profile.sub == "123"


@pytest.mark.asyncio
async def test_profile_http_error(oidc_service, mock_http_client, mock_metadata):
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_metadata),
        MagicMock(status_code=401),
    ]

    with pytest.raises(HTTPException) as exc:
        await oidc_service.profile("token")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_profile_validation_error(oidc_service, mock_http_client, mock_metadata):
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_metadata),
        MagicMock(status_code=200, json=lambda: {"sub": 123}),  # sub should be str
    ]

    # Actually pydantic might coerce int to str for sub, let's use missing field
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_metadata),
        MagicMock(status_code=200, json=lambda: {"name": "No Sub"}),
    ]

    with pytest.raises(HTTPException) as exc:
        await oidc_service.profile("token")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_logout_with_redirect(oidc_service, mock_access_token_cookie_session):
    response = await oidc_service.logout(redirect_uri="/login")

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_logout_without_redirect(oidc_service, mock_access_token_cookie_session):
    response = await oidc_service.logout(redirect_uri=None)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200


def test_relative_non_login_path(oidc_service):
    assert oidc_service._relative_non_login_path("/dashboard") == "/dashboard"
    assert (
        oidc_service._relative_non_login_path("/dashboard?foo=bar")
        == "/dashboard?foo=bar"
    )
    assert (
        oidc_service._relative_non_login_path("http://example.com/dashboard")
        == "/dashboard"
    )
    assert oidc_service._relative_non_login_path("/login") is None
    assert oidc_service._relative_non_login_path("/logout") is None
    assert oidc_service._relative_non_login_path("/foo/login") is None
    assert oidc_service._relative_non_login_path("http://example.com/foo/login") is None
    assert oidc_service._relative_non_login_path("/login/") is None
