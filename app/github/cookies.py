from app.config import config
from app.github.models import GithubPendingAuthSession, GitHubAccessTokenSession
from app.utils.api_cookie import APIKeyCookieModel


class GithubPendingAuthCookieSession(APIKeyCookieModel[GithubPendingAuthSession]):
    @property
    def payload_model(self) -> type[GithubPendingAuthSession]:
        return GithubPendingAuthSession


class GithubAccessTokenCookieSession(APIKeyCookieModel[GitHubAccessTokenSession]):
    @property
    def payload_model(self) -> type[GitHubAccessTokenSession]:
        return GitHubAccessTokenSession


github_pending_auth_cookie_session = GithubPendingAuthCookieSession(
    name="github_pending_auth_session", secret=config.secret_key.get_secret_value()
)

github_access_token_cookie_session = GithubAccessTokenCookieSession(
    name="github_access_token_session", secret=config.secret_key.get_secret_value()
)
