from app.config import config
from app.oidc.models import OIDCAccessTokenSession, OIDCPendingAuthSession
from app.utils.api_cookie import APIKeyCookieModel


class OIDCAccessTokenCookieSession(APIKeyCookieModel[OIDCAccessTokenSession]):
    @property
    def payload_model(self) -> type[OIDCAccessTokenSession]:
        return OIDCAccessTokenSession


class OIDCPendingAuthCookieSession(APIKeyCookieModel[OIDCPendingAuthSession]):
    @property
    def payload_model(self) -> type[OIDCPendingAuthSession]:
        return OIDCPendingAuthSession


oidc_access_token_cookie_session = OIDCAccessTokenCookieSession(
    name="canonical_oidc_session", secret=config.secret_key.get_secret_value()
)

oidc_pending_auth_cookie_session = OIDCPendingAuthCookieSession(
    name="canonical_oidc_login_session", secret=config.secret_key.get_secret_value()
)
