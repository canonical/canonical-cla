import json
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.config import config
from app.emails.blocked.excluded_emails import excluded_email
from app.github.models import GitHubAccessTokenResponse, GitHubProfile
from app.utils import EncryptedAPIKeyCookie, http_client


class GithubOAuthCookieSession(EncryptedAPIKeyCookie):
    pass


github_cookie_session = GithubOAuthCookieSession(
    name="github_oauth2_session", secret=config.secret_key.get_secret_value()
)


class GithubService:
    """
    Github OAuth2 service.
    Docs: https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
    """

    def __init__(
        self, cookie_session: GithubOAuthCookieSession, http_client: httpx.AsyncClient
    ):
        self.cookie_session = cookie_session
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
        self.cookie_session.set_cookie(
            response,
            value=json.dumps({"state": state, "redirect_url": redirect_url}),
            max_age=600,  # 10 minutes (GitHub OAuth2 session timeout)
            httponly=True,
        )
        return response

    async def callback(
        self,
        code: str,
    ) -> str:
        access_token_data = {
            "client_id": config.github_oauth.client_id,
            "client_secret": config.github_oauth.client_secret.get_secret_value(),
            "code": code,
        }
        response = (
            await self.http_client.post(
                url="https://github.com/login/oauth/access_token",
                json=access_token_data,
                headers={"Accept": "application/json"},
            )
        ).json()
        if "error" in response:
            raise HTTPException(
                status_code=400, detail=f"Bad Request: {response['error_description']}"
            )
        access_token_response = GitHubAccessTokenResponse(**response)
        return access_token_response["access_token"]

    async def profile(self, access_token: str) -> GitHubProfile:
        response = await self.http_client.get(
            url="https://api.github.com/user/emails",
            headers={"Authorization": f"bearer {access_token}"},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get emails from GitHub",
            )
        emails = response.json()
        all_emails = [
            email["email"]
            for email in emails
            if email["verified"] and not excluded_email(email["email"])
        ]

        user = await self.http_client.get(
            url="https://api.github.com/user",
            headers={"Authorization": f"bearer {access_token}"},
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

    def encrypt(self, value: str) -> str:
        return self.cookie_session.cipher.encrypt(value)


async def github_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> GithubService:
    return GithubService(github_cookie_session, http_client)
