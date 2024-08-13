import json
from typing import TypedDict

from fastapi import Response
from launchpadlib.credentials import (AccessToken, Credentials,
                                      CredentialStore,
                                      RequestTokenAuthorizationEngine)

from app.launchpad.literals import ACCESS_LEVELS, CONSUMER_KEY, SERVICE_ROOT
from app.utils import EncryptedAPIKeyCookie


class Token(TypedDict):
    key: str
    secret: str


class AccessTokenDict(Token):
    pass


class RequestTokenDict(Token):
    pass


class StoreItem(TypedDict):
    access_token: AccessTokenDict | None
    oauth_token: RequestTokenDict | None


class ReinitializableCredentials(Credentials):
    """Store Launchpad OAuth credentials object in a database or a cookie session."""

    def __init__(self, authorization_engine: RequestTokenAuthorizationEngine):
        super(ReinitializableCredentials, self).__init__(
            consumer_name=authorization_engine.application_name
        )

    def decode_token(self) -> StoreItem | None:
        """
        Decodes the Launchpad credentials object into a dictionary.
        """
        store_item: StoreItem = {}

        if self._request_token:
            store_item["oauth_token"] = {
                "key": self._request_token.key,
                "secret": self._request_token.secret,
            }
        if self.access_token:
            store_item["access_token"] = {
                "key": self.access_token.key,
                "secret": self.access_token.secret,
            }
        if store_item == {}:
            return None

        return store_item

    def load_token(self, token: StoreItem):
        """
        Load the token from the store (database or cookie session) as a Launchpad credentials object.
        """
        if token.get("oauth_token") is not None:
            self._request_token = AccessToken(
                key=token["oauth_token"]["key"], secret=token["oauth_token"]["secret"]
            )
        if token.get("access_token") is not None:
            self.access_token = AccessToken(
                key=token["access_token"]["key"], secret=token["access_token"]["secret"]
            )


auth_engine = RequestTokenAuthorizationEngine(
    service_root=SERVICE_ROOT,
    consumer_name=CONSUMER_KEY,
    allow_access_levels=ACCESS_LEVELS,
)


class UserCookieCredentialStore(CredentialStore):
    """
    Store credentials in an encrypted cookie session.
    """

    def __init__(
        self,
        response: Response,
        cookie_session: EncryptedAPIKeyCookie,
        oauth_token: StoreItem | None = None,
    ):
        super(UserCookieCredentialStore, self).__init__()
        self.response = response
        self.cookie_session = cookie_session
        self.oauth_token = oauth_token

    def do_save(
        self, credentials: ReinitializableCredentials, request_token: str | None = None
    ):
        """
        Override the do_save method to save the credentials in the cookie session.
        """
        oauth_token = credentials.decode_token()
        self.cookie_session.set_cookie(
            self.response,
            value=json.dumps(oauth_token),
            max_age=3600,  # 1 hour
            expires=12 * 3600,  # 12 hours
            path="/",
            domain=None,
            secure=False,
            httponly=True,
            samesite="lax",
        )

    def save_access_token(
        self, credentials: ReinitializableCredentials, access_token: AccessToken
    ):
        """
        Save the access token in the cookie session.
        """
        user_tokens = credentials.decode_token()
        if user_tokens is None or user_tokens.get("oauth_token") is None:
            # This should never happen, if save_access_token by launchpadlib
            raise ValueError("No request token found")
        user_tokens["access_token"] = {
            "key": access_token.key,
            "secret": access_token.secret,
        }
        self.cookie_session.set_cookie(
            self.response,
            value=json.dumps(user_tokens),
            max_age=12 * 3600,  # 1 hour
            expires=12 * 3600,  # 12 hours
            path="/",
            domain=None,
            secure=False,
            httponly=True,
            samesite="lax",
        )

    def do_load(self, request_token=None) -> ReinitializableCredentials | None:
        """
        Save the tokens into a credentials object.
        """
        if self.oauth_token is not None:
            credentials = ReinitializableCredentials(auth_engine)
            credentials.load_token(self.oauth_token)
            return credentials
        else:
            return None
