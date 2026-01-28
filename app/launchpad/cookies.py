from app.config import config
from app.launchpad.models import AccessTokenSession, RequestTokenSession
from app.utils.api_cookie import APIKeyCookieModel


class LaunchpadPendingAuthCookieSession(APIKeyCookieModel[RequestTokenSession]):
    @property
    def payload_model(self) -> type[RequestTokenSession]:
        return RequestTokenSession


class LaunchpadAccessTokenCookieSession(APIKeyCookieModel[AccessTokenSession]):
    @property
    def payload_model(self) -> type[AccessTokenSession]:
        return AccessTokenSession


launchpad_pending_auth_cookie_session = LaunchpadPendingAuthCookieSession(
    name="launchpad_pending_auth_session", secret=config.secret_key.get_secret_value()
)

launchpad_access_token_cookie_session = LaunchpadAccessTokenCookieSession(
    name="launchpad_access_token_session", secret=config.secret_key.get_secret_value()
)
