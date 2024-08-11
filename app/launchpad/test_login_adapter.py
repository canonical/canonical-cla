from unittest.mock import MagicMock

import pytest
from fastapi import Response
from launchpadlib.credentials import AccessToken
from literals import CONSUMER_KEY
from login_adapter import (
    AccessTokenDict,
    ReinitializableCredentials,
    RequestTokenDict,
    UserCookieCredentialStore,
    auth_engine,
)

from app.utils import EncryptedAPIKeyCookie


@pytest.fixture
def request_token():
    return RequestTokenDict(key="request-token-key", secret="request-token-secret")


@pytest.fixture
def access_token_dict():
    return AccessTokenDict(key="access-token-key", secret="access-token-secret")


@pytest.fixture
def access_token(access_token_dict):
    return AccessToken(key=access_token_dict["key"], secret=access_token_dict["secret"])


@pytest.fixture
def credentials():
    return ReinitializableCredentials(auth_engine)


@pytest.fixture
def cookie_session():
    return EncryptedAPIKeyCookie(name="testing-cookie", secret="super-secret")


@pytest.fixture
def response():
    return Response()


def test_reinitializable_credentials_initialization(credentials):
    """Test that ReinitializableCredentials is initialized correctly."""
    assert auth_engine.consumer.key == CONSUMER_KEY
    assert credentials.consumer.key == CONSUMER_KEY
    assert credentials._request_token is None
    assert credentials.access_token is None
    assert credentials.decode_token() is None


def test_reinitializable_credentials_loading_tokens(
    credentials, request_token, access_token_dict
):
    """Test loading and decoding tokens in ReinitializableCredentials."""
    credentials.load_token({"oauth_token": request_token})
    assert credentials._request_token.key == request_token["key"]
    assert credentials._request_token.secret == request_token["secret"]
    assert credentials.access_token is None

    credentials.load_token(
        {"oauth_token": request_token, "access_token": access_token_dict}
    )
    assert credentials.access_token.key == access_token_dict["key"]
    assert credentials.access_token.secret == access_token_dict["secret"]

    credentials._request_token = None
    credentials.load_token({"access_token": access_token_dict})
    assert credentials.access_token.key == access_token_dict["key"]
    assert credentials.access_token.secret == access_token_dict["secret"]
    assert credentials.decode_token() == {"access_token": access_token_dict}


def test_user_cookie_credential_store_save(
    request_token,
    access_token_dict,
    access_token,
    credentials,
    cookie_session,
    response,
):
    """Test saving credentials to a cookie using UserCookieCredentialStore."""
    credentials.decode_token = MagicMock(
        return_value={"oauth_token": request_token, "access_token": access_token_dict}
    )
    cookie_session.set_cookie = MagicMock()

    store = UserCookieCredentialStore(response, cookie_session)
    store.do_save(credentials)

    credentials.decode_token.assert_called_once()
    cookie_session.set_cookie.assert_called_once()

    credentials.decode_token = MagicMock(return_value={"oauth_token": request_token})
    cookie_session.set_cookie.reset_mock()

    store.save_access_token(credentials, access_token)

    credentials.decode_token.assert_called_once()
    cookie_session.set_cookie.assert_called_once()


def test_user_cookie_credential_store_save_access_token_error(
    credentials, access_token, cookie_session, response
):
    """Test that ValueError is raised when saving access token without oauth token."""
    credentials.decode_token = MagicMock(return_value=None)
    cookie_session.set_cookie = MagicMock()

    store = UserCookieCredentialStore(response, cookie_session)

    with pytest.raises(ValueError):
        store.save_access_token(credentials, access_token)

    credentials.decode_token.assert_called_once()
    cookie_session.set_cookie.assert_not_called()


def test_user_cookie_credential_store_load_tokens(
    request_token, access_token_dict, cookie_session, response
):
    """Test loading tokens from a cookie using UserCookieCredentialStore."""
    oauth_token = {"oauth_token": request_token, "access_token": access_token_dict}

    store = UserCookieCredentialStore(response, cookie_session, oauth_token)
    credentials = store.do_load()

    assert credentials._request_token.key == request_token["key"]
    assert credentials._request_token.secret == request_token["secret"]
    assert credentials.access_token.key == access_token_dict["key"]
    assert credentials.access_token.secret == access_token_dict["secret"]
    assert credentials.consumer.key == CONSUMER_KEY
