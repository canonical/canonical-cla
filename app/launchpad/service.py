import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.config import config
from app.launchpad.models import (
    AccessTokenSession,
    LaunchpadAccessTokenResponse,
    LaunchpadEmailListResponse,
    LaunchpadEmailResponse,
    LaunchpadPersonResponse,
    LaunchpadProfile,
    LaunchpadRequestTokenResponse,
    RequestTokenSession,
)
from app.utils import EncryptedAPIKeyCookie, http_client


class LaunchpadService:
    """
    Launchpad OAuth service.
    Docs: https://help.launchpad.net/API/SigningRequests
    """

    def __init__(
        self, cookie_session: EncryptedAPIKeyCookie, http_client: httpx.AsyncClient
    ):
        self.cookie_session = cookie_session
        self.http_client = http_client

    async def login(
        self, callback_url: str, redirect_url: str | None = None
    ) -> RedirectResponse:
        request_token_params = {
            "oauth_consumer_key": config.app_name,
            "oauth_signature_method": "PLAINTEXT",
            "oauth_signature": "&",
        }

        response = await self.http_client.post(
            "https://launchpad.net/+request-token",
            data=request_token_params,
            headers={"Accept": "application/json"},
        )
        response_body = response.text
        if response.status_code != 200 or not response_body:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get request token from Launchpad",
            )
        request_token_response = LaunchpadRequestTokenResponse(
            **json.loads(response_body)
        )
        state = secrets.token_urlsafe(16)
        authorize_token_params = urlencode(
            {
                "oauth_token": request_token_response["oauth_token"],
                "oauth_callback": f"{callback_url}?state={state}",
                "allow_permission": "READ_PRIVATE",
            }
        )

        response = RedirectResponse(
            url=f"https://launchpad.net/+authorize-token?{authorize_token_params}"
        )
        request_token_session = RequestTokenSession(
            oauth_token=request_token_response["oauth_token"],
            oauth_token_secret=request_token_response["oauth_token_secret"],
            state=state,
            redirect_url=redirect_url,
        )
        self.cookie_session.set_cookie(
            response,
            value=json.dumps(request_token_session),
            max_age=600,
            httponly=True,
        )
        return response

    async def callback(
        self,
        session_data: RequestTokenSession,
    ) -> LaunchpadAccessTokenResponse:
        access_token_params = {
            "oauth_consumer_key": config.app_name,
            "oauth_token": session_data["oauth_token"],
            "oauth_signature_method": "PLAINTEXT",
            "oauth_signature": f"&{session_data['oauth_token_secret']}",
        }
        response = await self.http_client.post(
            "https://launchpad.net/+access-token",
            data=access_token_params,
        )
        response_body = response.text
        if response.status_code != 200 or not response_body:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get access token from Launchpad",
            )
        access_token_response = LaunchpadAccessTokenResponse(
            **dict([pair.split("=") for pair in response_body.split("&")])
        )
        return access_token_response

    async def profile(self, session_data: AccessTokenSession) -> LaunchpadProfile:
        # Get user profile
        response = await self.http_client.get(
            "https://api.launchpad.net/1.0/people/+me",
            follow_redirects=True,
            headers=self.authorization_header(session_data),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user data from Launchpad",
            )
        user = LaunchpadPersonResponse(**response.json())

        # Get primary email
        response = await self.http_client.get(
            url=user["preferred_email_address_link"],
            follow_redirects=True,
            headers=self.authorization_header(session_data),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user primary email from Launchpad",
            )
        primary_email = LaunchpadEmailResponse(**response.json())["email"]

        # Get additional emails (returns empty list if no additional emails)
        # TODO: check if people reach pagination limit, which is highly unlikely
        response = await self.http_client.get(
            url=user["confirmed_email_addresses_collection_link"],
            follow_redirects=True,
            headers=self.authorization_header(session_data),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user emails from Launchpad",
            )
        email_list = LaunchpadEmailListResponse(**response.json())
        additional_emails = [entry["email"] for entry in email_list["entries"]]

        all_emails = [primary_email, *additional_emails]
        return LaunchpadProfile(
            _id=user["id"],
            username=user["name"],
            emails=all_emails,
        )

    def authorization_header(self, session_data: AccessTokenSession) -> dict[str, str]:
        return {
            "Authorization": ",".join(
                [
                    'OAuth realm="https://api.launchpad.net/"',
                    f'oauth_consumer_key="{config.app_name}"',
                    f'oauth_token="{session_data["oauth_token"]}"',
                    f'oauth_signature_method="PLAINTEXT"',
                    f'oauth_signature="&{session_data["oauth_token_secret"]}"',
                    f"oauth_timestamp={int(time.time())}",
                    f"oauth_nonce={secrets.randbelow(2**50)}",
                    'oauth_version="1.0"',
                ]
            )
        }

    def encrypt(self, value: str) -> str:
        return self.cookie_session.cipher.encrypt(value)


class LaunchpadOAuthCookieSession(EncryptedAPIKeyCookie):
    pass


launchpad_cookie_session = LaunchpadOAuthCookieSession(
    name="launchpad_oauth_session", secret=config.secret_key.get_secret_value()
)


async def launchpad_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> LaunchpadService:
    return LaunchpadService(launchpad_cookie_session, http_client)
