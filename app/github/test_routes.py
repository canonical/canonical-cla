import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL

from app.github.routes import (
    github_callback,
    github_emails,
    github_login,
    github_logout,
)


@pytest.mark.asyncio
async def test_login():
    github_service = MagicMock()
    github_service.login = AsyncMock(
        return_value=RedirectResponse(url="https://login-redirct.com")
    )

    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: "http://test.com/callback"
    response = await github_login(request, github_service)
    assert response.status_code == 307
    assert response.headers["location"] == "https://login-redirct.com"
    assert github_service.login.called


@pytest.mark.asyncio
async def test_callback_success():
    github_service = MagicMock()
    github_service.callback = AsyncMock(
        return_value=RedirectResponse(url="http://test.com/emails")
    )
    code = "test_code"
    state = "test_state"
    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: "http://test.com/emails"
    github_session = json.dumps({"state": state})
    response = await github_callback(
        request,
        code=code,
        state=state,
        github_session=github_session,
        github_service=github_service,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://test.com/emails"
    assert github_service.callback.called


@pytest.mark.asyncio
async def test_callback_invalid_params():
    github_service = MagicMock()
    github_service.callback = AsyncMock(
        return_value=RedirectResponse(url="http://test.com/emails")
    )
    code = None
    state = "test_state"
    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: "http://test.com/emails"
    github_session = json.dumps({"state": state})

    with pytest.raises(HTTPException):
        await github_callback(
            request,
            code=code,
            state=state,
            github_session=github_session,
            github_service=github_service,
        )

    assert not github_service.callback.called

    code = "test_code"
    state = None
    with pytest.raises(HTTPException):
        await github_callback(
            request,
            code=code,
            state=state,
            github_session=github_session,
            github_service=github_service,
        )

    assert not github_service.callback.called

    code = "test_code"
    state = "test_state"
    error_description = "Bad Request"
    with pytest.raises(HTTPException):
        await github_callback(
            request, code, state, error_description, github_session, github_service
        )
    assert not github_service.callback.called


@pytest.mark.asyncio
async def test_emails_success():
    github_service = MagicMock()
    github_service.emails = AsyncMock(return_value=["email1", "email2"])
    github_session = json.dumps({"access_token": "test_access_token"})
    response = await github_emails(github_session, github_service)
    assert response == ["email1", "email2"]
    assert github_service.emails.called


@pytest.mark.asyncio
async def test_emails_invalid_params():
    github_service = MagicMock()
    github_service.emails = AsyncMock(return_value=["email1", "email2"])
    github_session = None
    with pytest.raises(HTTPException):
        await github_emails(github_session, github_service)

    assert not github_service.emails.called


@pytest.mark.asyncio
async def test_logout():
    request = Request({"url": "http://test.com", "type": "http", "router": "github"})
    request.url_for = lambda x: URL("http://test.com/login")
    response = await github_logout(request)

    assert response.status_code == 200
