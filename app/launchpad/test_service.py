import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.launchpad.models import (
    AccessTokenSession,
    LaunchpadAccessTokenResponse,
    RequestTokenSession,
)
from app.launchpad.service import LaunchpadService
from app.utils import EncryptedAPIKeyCookie


@pytest.fixture
def cookie_session():
    return EncryptedAPIKeyCookie(name="test_cookie", secret="supersecret")


@pytest.fixture
def access_token_session():
    return AccessTokenSession(
        oauth_token="test_token",
        oauth_token_secret="test_secret",
    )


@pytest.fixture
def request_token_session():
    return RequestTokenSession(
        oauth_token="test_token", oauth_token_secret="test_secret", state="test_state"
    )


@patch("secrets.token_urlsafe", return_value="test_state")
@pytest.mark.asyncio
async def test_login_success(token_urlsafe):
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            text=json.dumps(
                {
                    "oauth_token": "test_token",
                    "oauth_token_secret": "test_secret",
                }
            ),
        )
    )
    launchpad_service = LaunchpadService(cookie_session, http_client)
    response = await launchpad_service.login(
        callback_url="http://test.com", redirect_url="not_used_in_this_test"
    )
    assert http_client.post.called
    assert cookie_session.set_cookie.called
    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "https://launchpad.net/+authorize-token?oauth_token=test_token&oauth_callback=http%3A%2F%2Ftest.com%3Fstate%3Dtest_state&allow_permission=READ_PRIVATE"
    )


@pytest.mark.asyncio
async def test_login_failure():
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=httpx.Response(status_code=500))
    launchpad_service = LaunchpadService(cookie_session, http_client)
    with pytest.raises(HTTPException):
        await launchpad_service.login("http://test.com", "not_used_in_this_test")
    assert cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_callback_success(cookie_session, request_token_session):
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            text="oauth_token=test_token&oauth_token_secret=test_secret",
        )
    )
    launchpad_service = LaunchpadService(cookie_session, http_client)
    response = await launchpad_service.callback(request_token_session)
    assert http_client.post.called
    assert response == LaunchpadAccessTokenResponse(
        oauth_token="test_token", oauth_token_secret="test_secret"
    )


@pytest.mark.asyncio
async def test_callback_failure(cookie_session, request_token_session):
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=httpx.Response(status_code=500))
    launchpad_service = LaunchpadService(cookie_session, http_client)
    with pytest.raises(HTTPException):
        await launchpad_service.callback(request_token_session)


@pytest.mark.asyncio
async def test_profile_success(cookie_session, access_token_session):
    cookie_session = MagicMock()
    http_client = MagicMock()
    mock_responses = {
        "https://api.launchpad.net/1.0/people/+me": {
            "status_code": 200,
            "json": {
                "id": "test_id",
                "name": "test_username",
                "preferred_email_address_link": "preferred_email_url.com",
                "confirmed_email_addresses_collection_link": "conformed_email_url.com",
            },
        },
        "preferred_email_url.com": {
            "status_code": 200,
            "json": {"email": "primary@email.com"},
        },
        "conformed_email_url.com": {
            "status_code": 200,
            "json": {
                "entries": [{"email": "name1@email.com"}, {"email": "name2@email.com"}]
            },
        },
    }
    http_client.get = AsyncMock(
        side_effect=lambda url, **kwargs: httpx.Response(
            status_code=mock_responses[url]["status_code"],
            json=mock_responses[url]["json"],
        )
    )
    launchpad_service = LaunchpadService(cookie_session, http_client)
    response = await launchpad_service.profile(access_token_session)
    assert response.model_dump() == {
        "username": "test_username",
        "emails": ["primary@email.com", "name1@email.com", "name2@email.com"],
    }
    assert http_client.get.call_count == 3
    assert cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_profile_failure(cookie_session, access_token_session):
    cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=httpx.Response(status_code=500))
    launchpad_service = LaunchpadService(cookie_session, http_client)
    with pytest.raises(HTTPException):
        await launchpad_service.profile(access_token_session)
    assert cookie_session.set_cookie.called is False
