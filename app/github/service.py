import json
import secrets
from typing import List
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.config import config
from app.github.models import GitHubAccessTokenResponse
from app.utils import EncryptedAPIKeyCookie, http_client


class GithubService:
    """
    Github OAuth2 service.
    Docs: https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
    """

    def __init__(
        self, cookie_session: EncryptedAPIKeyCookie, http_client: httpx.AsyncClient
    ):
        self.cookie_session = cookie_session
        self.http_client = http_client

    async def login(self, callback_url: str) -> RedirectResponse:
        print(callback_url)
        state = secrets.token_urlsafe(16)
        params = urlencode(
            {
                "client_id": config.github_oauth.client_id,
                "scope": config.github_oauth.scope,
                "redirect_uri": callback_url,
                "state": state,
            }
        )
        print(params)
        response = RedirectResponse(
            url=f"https://github.com/login/oauth/authorize?{params}"
        )
        self.cookie_session.set_cookie(
            response,
            value=json.dumps({"state": state}),
            max_age=600,  # 10 minutes (GitHub OAuth2 session timeout)
            httponly=True,
        )
        return response

    async def callback(self, code: str, emails_url: str) -> RedirectResponse:
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
        emails_response = RedirectResponse(url=emails_url)
        self.cookie_session.set_cookie(
            emails_response,
            value=access_token_response["access_token"],
            httponly=True,
        )
        return emails_response

    async def emails(self, access_token: str) -> List[str]:
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
        return [email["email"] for email in emails if email["verified"]]


github_cookie_session = EncryptedAPIKeyCookie(
    name="github_oauth2_session", secret=config.secret_key.get_secret_value()
)


async def github_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> GithubService:
    return GithubService(github_cookie_session, http_client)
