from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.oidc.models import OIDCMetadata
from app.oidc.service import OIDCService

MOCK_METADATA: OIDCMetadata = {
    "issuer": "https://login.canonical.com",
    "authorization_endpoint": "https://login.canonical.com/authorize",
    "token_endpoint": "https://login.canonical.com/token",
    "userinfo_endpoint": "https://login.canonical.com/userinfo",
    "jwks_uri": "https://login.canonical.com/.well-known/jwks.json",
}


@pytest.fixture
def oidc_service():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(
        return_value=httpx.Response(status_code=200, json=MOCK_METADATA)
    )
    return OIDCService(cookie_session, http_client)


@pytest.mark.asyncio
async def test_get_metadata_success(oidc_service):
    metadata = await oidc_service._get_metadata()
    assert metadata == MOCK_METADATA
    assert oidc_service.http_client.get.called


@pytest.mark.asyncio
async def test_get_metadata_failure():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=httpx.Response(status_code=500))
    service = OIDCService(cookie_session, http_client)

    with pytest.raises(HTTPException) as exc:
        await service._get_metadata()
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_get_metadata_caches_result(oidc_service):
    await oidc_service._get_metadata()
    await oidc_service._get_metadata()
    assert oidc_service.http_client.get.call_count == 1


@patch("secrets.token_urlsafe", return_value="test_state_nonce")
@patch("app.config.config.canonical_oidc.client_id", "test_client_id")
@patch("app.config.config.canonical_oidc.scope", "openid profile email")
@pytest.mark.asyncio
async def test_login_success(mock_token, oidc_service):
    response = await oidc_service.login(
        "http://test.com/callback", "http://test.com/redirect"
    )

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://login.canonical.com/authorize")
    assert "test_client_id" in location
    assert "test_state_nonce" in location
    assert "openid" in location
    assert oidc_service.cookie_session.set_cookie.called


@patch("secrets.token_urlsafe", return_value="test_state_nonce")
@pytest.mark.asyncio
async def test_login_sets_cookie_with_state(mock_token, oidc_service):
    await oidc_service.login("http://test.com/callback", "http://test.com/redirect")

    call_args = oidc_service.cookie_session.set_cookie.call_args
    cookie_value = call_args.kwargs["value"]
    assert "test_state_nonce" in cookie_value
    assert "http://test.com/redirect" in cookie_value


@patch("app.config.config.canonical_oidc.client_id", "test_client_id")
@patch(
    "app.config.config.canonical_oidc.client_secret.get_secret_value",
    lambda: "test_secret",
)
@pytest.mark.asyncio
async def test_callback_success(oidc_service):
    oidc_service.http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json={"access_token": "test_access_token", "token_type": "Bearer"},
        )
    )

    access_token = await oidc_service.callback("test_code", "http://test.com/callback")

    assert access_token == "test_access_token"
    assert oidc_service.http_client.post.called


@pytest.mark.asyncio
async def test_callback_token_exchange_failure(oidc_service):
    oidc_service.http_client.post = AsyncMock(
        return_value=httpx.Response(status_code=400, text="Bad Request")
    )

    with pytest.raises(HTTPException) as exc:
        await oidc_service.callback("test_code", "http://test.com/callback")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_callback_token_error_response(oidc_service):
    oidc_service.http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json={"error": "invalid_grant", "error_description": "Code expired"},
        )
    )

    with pytest.raises(HTTPException) as exc:
        await oidc_service.callback("test_code", "http://test.com/callback")
    assert exc.value.status_code == 400
    assert "Code expired" in exc.value.detail


@pytest.mark.asyncio
async def test_profile_success(oidc_service):
    oidc_service.http_client.get = AsyncMock(
        side_effect=[
            httpx.Response(status_code=200, json=MOCK_METADATA),
            httpx.Response(
                status_code=200,
                json={
                    "sub": "user123",
                    "email": "user@canonical.com",
                    "email_verified": True,
                    "name": "Test User",
                    "preferred_username": "testuser",
                    "picture": "https://example.com/pic.jpg",
                    "given_name": "Test",
                    "family_name": "User",
                },
            ),
        ]
    )
    # Reset cached metadata
    oidc_service._metadata = None

    profile = await oidc_service.profile("test_access_token")

    assert profile.sub == "user123"
    assert profile.email == "user@canonical.com"
    assert profile.email_verified is True
    assert profile.name == "Test User"
    assert profile.username == "testuser"
    assert profile.picture == "https://example.com/pic.jpg"
    assert profile.given_name == "Test"
    assert profile.family_name == "User"


@pytest.mark.asyncio
async def test_profile_failure(oidc_service):
    oidc_service.http_client.get = AsyncMock(
        side_effect=[
            httpx.Response(status_code=200, json=MOCK_METADATA),
            httpx.Response(status_code=401),
        ]
    )
    oidc_service._metadata = None

    with pytest.raises(HTTPException) as exc:
        await oidc_service.profile("invalid_token")
    assert exc.value.status_code == 401


def test_encrypt():
    cookie_session = MagicMock()
    cookie_session.cipher.encrypt.return_value = "encrypted_value"
    http_client = MagicMock()
    service = OIDCService(cookie_session, http_client)

    result = service.encrypt("test_value")

    assert result == "encrypted_value"
    cookie_session.cipher.encrypt.assert_called_once_with("test_value")
