import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL

from app.launchpad.routes import (
    launchpad_callback,
    launchpad_emails,
    launchpad_login,
    launchpad_logout,
)


@pytest.mark.asyncio
async def test_login():
    launchpad_service = MagicMock()
    launchpad_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    request = Request(
        {"url": "http://test.com/login", "type": "http", "router": "launchpad"}
    )
    request.url_for = lambda x: "http://test.com/callback"
    response = await launchpad_login(request, launchpad_service)
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert launchpad_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    launchpad_service = MagicMock()
    launchpad_service.callback = AsyncMock(
        return_value=RedirectResponse(url="http://test.com/emails")
    )
    state = "test_state"
    request = Request(
        {"url": "http://test.com/callback", "type": "http", "router": "launchpad"}
    )
    request.url_for = lambda x: "http://test.com/emails"
    launchpad_session = json.dumps({"state": state})
    response = await launchpad_callback(
        request, state, launchpad_session, launchpad_service
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com/emails"
    assert launchpad_service.callback.called


@pytest.mark.asyncio
async def test_callback_invalid_params():
    launchpad_service = MagicMock()
    launchpad_service.callback = AsyncMock(
        return_value=RedirectResponse(url="http://test.com/emails")
    )
    state = None
    request = Request(
        {"url": "http://test.com/callback", "type": "http", "router": "launchpad"}
    )
    launchpad_session = json.dumps({"state": "test_state"})
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called

    state = "test_state"
    launchpad_session = None
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called

    state = "invalid_test_state"
    launchpad_session = json.dumps({"state": "test_state"})
    with pytest.raises(HTTPException):
        await launchpad_callback(request, state, launchpad_session, launchpad_service)

    assert not launchpad_service.callback.called


@pytest.mark.asyncio
async def test_emails():
    launchpad_service = MagicMock()
    launchpad_service.emails = AsyncMock(return_value=["email1", "email2"])

    request = Request(
        {"url": "http://test.com/emails", "type": "http", "router": "launchpad"}
    )
    launchpad_session = json.dumps({"state": "test_state"})
    response = await launchpad_emails(launchpad_session, launchpad_service)
    assert response == ["email1", "email2"]
    assert launchpad_service.emails.called

    launchpad_session = None
    launchpad_service.emails.reset_mock()
    with pytest.raises(HTTPException):
        await launchpad_emails(launchpad_session, launchpad_service)

    assert not launchpad_service.emails.called


@pytest.mark.asyncio
async def test_logout():
    request = Request(
        {"url": "http://test.com/logout", "type": "http", "router": "launchpad"}
    )
    request.url_for = lambda x: URL("http://test.com/login")
    response = await launchpad_logout(request)
    assert response.status_code == 200
