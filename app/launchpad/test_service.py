from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.launchpad.models import (
    AccessTokenSession,
    RequestTokenSession,
)
from app.launchpad.service import LaunchpadService


@pytest.fixture
def access_token_session():
    return AccessTokenSession(
        oauth_token="test_token",
        oauth_token_secret="test_secret",
    )


@pytest.fixture
def request_token_session():
    return RequestTokenSession(
        oauth_token="test_token",
        oauth_token_secret="test_secret",
        state="test_state",
        redirect_url="http://test.com/redirect",
    )


@patch("secrets.token_urlsafe", return_value="test_state")
@pytest.mark.asyncio
async def test_login_success(token_urlsafe):
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "oauth_token": "test_token",
                "oauth_token_secret": "test_secret",
                "oauth_token_consumer": "test_consumer",
            },
        )
    )
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    response = await launchpad_service.login(
        callback_url="http://test.com", redirect_url="not_used_in_this_test"
    )
    assert http_client.post.called
    assert pending_auth_cookie_session.set_cookie.called
    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "https://launchpad.net/+authorize-token?oauth_token=test_token&oauth_callback=http%3A%2F%2Ftest.com%3Fstate%3Dtest_state&allow_permission=READ_PRIVATE"
    )


@pytest.mark.asyncio
async def test_login_failure():
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=httpx.Response(status_code=500, text="err"))
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    with pytest.raises(HTTPException):
        await launchpad_service.login("http://test.com", "not_used_in_this_test")
    assert pending_auth_cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_callback_success(request_token_session):
    pending_auth_cookie_session = MagicMock()
    pending_auth_cookie_session.name = "launchpad_pending_auth_session"
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            text="oauth_token=test_token&oauth_token_secret=test_secret",
        )
    )
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    response = await launchpad_service.callback(
        oauth_token=request_token_session.oauth_token,
        oauth_token_secret=request_token_session.oauth_token_secret,
        redirect_url=request_token_session.redirect_url,
    )
    assert http_client.post.called
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com/redirect"
    assert access_token_cookie_session.set_cookie.called is True


@pytest.mark.asyncio
async def test_callback_failure(request_token_session):
    pending_auth_cookie_session = MagicMock()
    pending_auth_cookie_session.name = "launchpad_pending_auth_session"
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=httpx.Response(status_code=500, text="err"))
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    with pytest.raises(HTTPException):
        await launchpad_service.callback(
            oauth_token=request_token_session.oauth_token,
            oauth_token_secret=request_token_session.oauth_token_secret,
            redirect_url=request_token_session.redirect_url,
        )


@pytest.mark.asyncio
async def test_profile_success(access_token_session):
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    mock_responses: dict[str, dict] = {
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
            "json": {
                "self_link": "self",
                "web_link": "web",
                "resource_type_link": "type",
                "email": "primary@email.com",
                "person_link": "person",
                "http_etag": "etag",
            },
        },
        "conformed_email_url.com": {
            "status_code": 200,
            "json": {
                "entries": [
                    {
                        "self_link": "self1",
                        "web_link": "web1",
                        "resource_type_link": "type",
                        "email": "name1@email.com",
                        "person_link": "person",
                        "http_etag": "etag",
                    },
                    {
                        "self_link": "self2",
                        "web_link": "web2",
                        "resource_type_link": "type",
                        "email": "name2@email.com",
                        "person_link": "person",
                        "http_etag": "etag",
                    },
                ],
                "start": 0,
                "total_size": 2,
                "resource_type_link": "collection",
            },
        },
    }
    http_client.get = AsyncMock(
        side_effect=lambda url, **kwargs: httpx.Response(
            status_code=mock_responses[url]["status_code"],
            json=mock_responses[url]["json"],
        )
    )
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    response = await launchpad_service.profile(access_token_session)
    assert response.model_dump() == {
        "username": "test_username",
        "emails": ["primary@email.com", "name1@email.com", "name2@email.com"],
    }
    assert http_client.get.call_count == 3
    assert access_token_cookie_session.set_cookie.called is False


@pytest.mark.asyncio
async def test_profile_failure(access_token_session):
    pending_auth_cookie_session = MagicMock()
    access_token_cookie_session = MagicMock()
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=httpx.Response(status_code=500))
    launchpad_service = LaunchpadService(
        pending_auth_cookie_session, access_token_cookie_session, http_client
    )
    with pytest.raises(HTTPException):
        await launchpad_service.profile(access_token_session)
    assert access_token_cookie_session.set_cookie.called is False
