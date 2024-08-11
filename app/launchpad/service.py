import logging
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from launchpadlib.launchpad import Launchpad
from lazr.restfulclient.errors import HTTPError, Unauthorized

from app.config import config
from app.launchpad.literals import (
    ACCESS_LEVELS,
    COOKIE_SESSION_NAME,
    SERVICE_ROOT,
    WEB_ROOT,
)
from app.launchpad.login_adapter import (
    ReinitializableCredentials,
    StoreItem,
    UserCookieCredentialStore,
    auth_engine,
)
from app.launchpad.models import LPUser
from app.utils import EncryptedAPIKeyCookie


class LaunchpadService:
    _cookie_session = EncryptedAPIKeyCookie(
        name=COOKIE_SESSION_NAME, secret=config.secret_key.get_secret_value()
    )
    _logger = logging.getLogger(__name__)

    def logout(self, response: Response) -> None:
        """
        Remove the access token from the cookie session.

        :param response: the response object to remove the cookie.
        """
        response.delete_cookie(COOKIE_SESSION_NAME)

    def login_redirect(self, request: Request) -> RedirectResponse:
        """
        Initiate the Launchpad login process.

        :param request: the request object to retrieve the service hostname.

        :return: the redirection response.
        """
        credentials = ReinitializableCredentials(auth_engine)
        request_token = credentials.get_request_token(
            web_root=WEB_ROOT, token_format=ReinitializableCredentials.DICT_TOKEN_FORMAT
        )
        oauth_token = request_token["oauth_token"]
        callback_url = (
            f"{request.url_for('launchpad_callback')}?request_token={oauth_token}"
        )

        params = urlencode(
            {
                "oauth_token": oauth_token,
                "oauth_callback": callback_url,
                "allow_permission": ACCESS_LEVELS,
            }
        )

        response = RedirectResponse(
            url=f"https://launchpad.net/+authorize-token?{params}"
        )
        store = UserCookieCredentialStore(response, self._cookie_session)
        store.do_save(credentials)
        return response

    def login_callback(
        self, user_tokens: StoreItem, callback_token: str, whoami_url: str
    ) -> RedirectResponse:
        """
        Save the access token in the cookie session.

        :param user_tokens: the user tokens from the cookie session.
        :param callback_token: the request token from the callback URL.

        :return: the redirection response.
        :raises ValueError: if the request token is invalid.
        """
        redirect_response = RedirectResponse(url=whoami_url)
        store = UserCookieCredentialStore(
            redirect_response, self._cookie_session, user_tokens
        )
        credentials = store.do_load()
        if callback_token != credentials._request_token.key:
            self._logger.info(
                f"Invalid request token: {callback_token[:8]}.. != {credentials._request_token.key[:8]}.."
            )
            raise ValueError("Invalid request token")
        elif credentials.access_token is not None:
            # already logged in with this request token
            # continuing further will return an error from the launchpad API
            return redirect_response
        try:
            credentials.exchange_request_token_for_access_token(web_root=WEB_ROOT)
            store.save_access_token(credentials, credentials.access_token)
            return redirect_response

        except HTTPError as e:
            self._logger.info(f"OAuth token exchange failed: {e}")
            raise ValueError("OAuth token exchange failed")

    def whoami(self, response: Response, user_tokens: StoreItem) -> dict | None:
        """
        Get the user details from Launchpad.

        :param response: the response object to store the cookie.
        :param user_tokens: the user tokens from the cookie session.

        :return: the user details from Launchpad's API.
        """
        store = UserCookieCredentialStore(
            response, LaunchpadService.launchpad_oauth_cookie_session(), user_tokens
        )
        credentials = store.do_load()
        lp = Launchpad(
            credentials,
            service_root=SERVICE_ROOT,
            credential_store=store,
            authorization_engine=auth_engine,
        )
        try:
            user = lp.me
            user_dict: LPUser = {}
            for key in LPUser.__annotations__:
                user_dict[key] = getattr(user, key)
            user_dict["preferred_email_address_link"] = user_dict[
                "preferred_email_address_link"
            ].split("/")[-1]
            return user_dict
        except Unauthorized as e:
            self._logger.info(f"Unauthorized: {e}")
            return None

    @staticmethod
    def launchpad_oauth_cookie_session():
        """
        Return the cookie session.
        """
        return LaunchpadService._cookie_session
