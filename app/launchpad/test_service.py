from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, Response
from launchpadlib.credentials import AccessToken

from app.launchpad.login_adapter import (
    AccessTokenDict,
    ReinitializableCredentials,
    RequestTokenDict,
    UserCookieCredentialStore,
    auth_engine,
)
from app.launchpad.service import LaunchpadService
from app.utils import EncryptedAPIKeyCookie


@pytest.fixture
def launchpad_service():
    return LaunchpadService()


@pytest.fixture
def http_response():
    return Response()


@pytest.fixture
def http_request():
    return Request(scope={"type": "http", "method": "GET"})


@pytest.fixture
def cookie_session():
    return EncryptedAPIKeyCookie(name="testing-cookie", secret="super-secret")


@pytest.fixture
def store(http_response, cookie_session):
    return UserCookieCredentialStore(http_response, cookie_session)


@pytest.fixture
def request_token():
    return RequestTokenDict(key="request-token-key", secret="request-token-secret")


@pytest.fixture
def access_token():
    return AccessTokenDict(key="access-token-key", secret="access-token-secret")


@pytest.fixture
def credentials(request_token):
    credentials_obj = ReinitializableCredentials(auth_engine)
    credentials_obj._request_token = AccessToken(
        key=request_token["key"], secret=request_token["secret"]
    )
    return credentials_obj


def test_logout(launchpad_service, http_response):
    http_response.delete_cookie = MagicMock()
    launchpad_service.logout(http_response)
    http_response.delete_cookie.assert_called_once()


@patch("app.launchpad.login_adapter.UserCookieCredentialStore.do_save")
@patch("app.launchpad.login_adapter.ReinitializableCredentials.get_request_token")
def test_login_redirect(
    mock_do_save, mock_get_request_token, launchpad_service, http_request
):
    http_request.url_for = MagicMock(return_value="http://localhost/callback")
    credentials.get_request_token = MagicMock(return_value={"oauth_token": "token"})
    store.do_save = MagicMock()
    http_response = launchpad_service.login_redirect(http_request)

    mock_get_request_token.assert_called_once()
    mock_do_save.assert_called_once()

    assert http_response.status_code == 307


@patch("app.launchpad.login_adapter.UserCookieCredentialStore.save_access_token")
@patch(
    "app.launchpad.login_adapter.ReinitializableCredentials.exchange_request_token_for_access_token"
)
@patch("app.launchpad.login_adapter.UserCookieCredentialStore.do_load")
def test_login_callback(
    mock_do_load,
    mock_exchange_request_token,
    mock_save_access_token,
    credentials,
    launchpad_service,
    request_token,
):
    mock_do_load.return_value = credentials
    http_response = launchpad_service.login_callback(
        user_tokens={"oauth_token": request_token},
        callback_token=request_token["key"],
        whoami_url="http://localhost/whoami",
    )

    mock_do_load.assert_called_once()
    mock_exchange_request_token.assert_called_once()
    mock_save_access_token.assert_called_once()

    assert http_response.status_code == 307
    assert http_response.headers.get("location") == "http://localhost/whoami"


@patch("app.launchpad.login_adapter.UserCookieCredentialStore.do_load")
def test_login_callback_incorrect_callback_token(
    mock_do_load, launchpad_service, credentials, store
):
    mock_do_load.return_value = credentials
    credentials.exchange_request_token_for_access_token = MagicMock()
    store.save_access_token = MagicMock()

    with pytest.raises(ValueError):
        launchpad_service.login_callback(
            user_tokens={"oauth_token": request_token},
            callback_token="incorrect-secret",
            whoami_url="http://localhost/whoami",
        )
    mock_do_load.assert_called_once()
    credentials.exchange_request_token_for_access_token.assert_not_called()
    store.save_access_token.assert_not_called()


@patch("app.launchpad.login_adapter.UserCookieCredentialStore.save_access_token")
@patch(
    "app.launchpad.login_adapter.ReinitializableCredentials.exchange_request_token_for_access_token"
)
@patch("app.launchpad.login_adapter.UserCookieCredentialStore.do_load")
def test_login_callback_already_logged_in(
    mock_do_load,
    mock_exchange_request_token,
    mock_save_access_token,
    credentials,
    launchpad_service,
    request_token,
    access_token,
):
    credentials.access_token = AccessToken(
        key=access_token["key"], secret=access_token["secret"]
    )
    mock_do_load.return_value = credentials
    http_response = launchpad_service.login_callback(
        user_tokens={"oauth_token": request_token, "access_token": access_token},
        callback_token=request_token["key"],
        whoami_url="http://localhost/whoami",
    )

    mock_do_load.assert_called_once()
    mock_exchange_request_token.assert_not_called()
    mock_save_access_token.assert_not_called()

    assert http_response.status_code == 307
    assert http_response.headers.get("location") == "http://localhost/whoami"
