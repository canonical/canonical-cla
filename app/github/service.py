import json
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import TypeAdapter, ValidationError

from app.config import config
from app.emails.blocked.excluded_emails import excluded_email
from app.github.cookies import (
    GithubAccessTokenCookieSession,
    GithubPendingAuthCookieSession,
    github_access_token_cookie_session,
    github_pending_auth_cookie_session,
)
from app.github.models import (
    GitHubAccessTokenResponse,
    GitHubAccessTokenSession,
    GitHubEmailResponse,
    GithubPendingAuthSession,
    GitHubProfile,
)
from app.http_client import http_client
from app.utils.request import update_query_params

logger = logging.getLogger(__name__)


class GithubService:
    """
    Github OAuth2 service.
    Docs: https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
    """

    def __init__(
        self,
        pending_auth_cookie_session: GithubPendingAuthCookieSession,
        access_token_cookie_session: GithubAccessTokenCookieSession,
        http_client: httpx.AsyncClient,
    ):
        self.pending_auth_cookie_session = pending_auth_cookie_session
        self.access_token_cookie_session = access_token_cookie_session
        self.http_client = http_client

    async def login(self, callback_url: str, redirect_url: str) -> RedirectResponse:
        state = secrets.token_urlsafe(16)
        params = urlencode(
            {
                "client_id": config.github_oauth.client_id,
                "scope": config.github_oauth.scope,
                "redirect_uri": callback_url,
                "state": state,
            }
        )
        response = RedirectResponse(
            url=f"https://github.com/login/oauth/authorize?{params}"
        )
        pending_auth_session = GithubPendingAuthSession(
            state=state, redirect_url=redirect_url
        )
        self.pending_auth_cookie_session.set_cookie(
            response,
            value=pending_auth_session,
            max_age=600,
        )
        return response

    async def callback(
        self,
        code: str,
        redirect_url: str,
    ) -> RedirectResponse:
        access_token_data = {
            "client_id": config.github_oauth.client_id,
            "client_secret": config.github_oauth.client_secret.get_secret_value(),
            "code": code,
        }
        response = await self.http_client.post(
            url="https://github.com/login/oauth/access_token",
            json=access_token_data,
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Unauthorized(GitHub): Not authenticated"
                if response.status_code == 401
                else f"Failed to get access token from GitHub: {response.text}",
            )

        if "error" in response.json():
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get access token from GitHub: {response.json()['error']}",
            )
        try:
            access_token_session = GitHubAccessTokenResponse.model_validate(
                response.json()
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate access token response from GitHub: {e}",
            ) from e
        access_token_session = GitHubAccessTokenSession.model_validate(
            access_token_session.model_dump()
        )
        # XXX: This is a hack to get the access token into the redirect URL
        # Remove this once we migrate the CLA form over to this domain
        redirect_url_is_absolute = redirect_url.startswith("http")
        redirect_url_is_external = (
            redirect_url_is_absolute and not redirect_url.startswith(config.app_url)
        )
        if redirect_url_is_external:
            redirect_url = update_query_params(
                redirect_url,
                access_token=self.access_token_cookie_session.cipher.encrypt(
                    json.dumps(access_token_session.model_dump())
                ),
            )
        response = RedirectResponse(url=redirect_url)

        self.access_token_cookie_session.set_cookie(
            response,
            value=access_token_session,
        )
        response.delete_cookie(key=self.pending_auth_cookie_session.name)
        return response

    async def profile(self, access_token: GitHubAccessTokenSession) -> GitHubProfile:
        response = await self.http_client.get(
            url="https://api.github.com/user/emails",
            headers={"Authorization": f"bearer {access_token.access_token}"},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get emails from GitHub",
            )
        try:
            emails: list[GitHubEmailResponse] = TypeAdapter(
                list[GitHubEmailResponse]
            ).validate_python(response.json())
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate emails from GitHub: {e}",
            ) from e

        all_emails: list[str] = [
            email.email
            for email in emails
            if email.verified and not excluded_email(email.email)
        ]

        user = await self.http_client.get(
            url="https://api.github.com/user",
            headers={"Authorization": f"bearer {access_token.access_token}"},
        )
        if user.status_code != 200:
            raise HTTPException(
                status_code=user.status_code,
                detail="Failed to get user profile from GitHub",
            )
        user_data = user.json()
        return GitHubProfile(
            _id=user_data["id"],
            username=user_data["login"],
            emails=all_emails,
        )

    def logout(self, redirect_url: str | None) -> RedirectResponse | JSONResponse:
        response: RedirectResponse | JSONResponse
        if redirect_url:
            response = RedirectResponse(url=redirect_url)
        else:
            response = JSONResponse(
                content={
                    "message": "Logged out",
                    "login_url": f"{config.app_url}/github/login",
                }
            )
        response.delete_cookie(key=self.access_token_cookie_session.name)
        return response


async def github_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> GithubService:
    return GithubService(
        github_pending_auth_cookie_session,
        github_access_token_cookie_session,
        http_client,
    )


async def optional_github_user(
    github_access_token_session: GitHubAccessTokenSession | None = Depends(
        github_access_token_cookie_session
    ),
    github_service: GithubService = Depends(github_service),
) -> GitHubProfile | None:
    if github_access_token_session is None:
        return None
    return await github_service.profile(access_token=github_access_token_session)


async def github_user(
    github_access_token_session: GitHubAccessTokenSession | None = Depends(
        github_access_token_cookie_session
    ),
    github_service: GithubService = Depends(github_service),
) -> GitHubProfile:
    user = await optional_github_user(github_access_token_session, github_service)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
