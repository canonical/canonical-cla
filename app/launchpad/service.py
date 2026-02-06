import json
import logging
import secrets
import time
from urllib.parse import parse_qsl, urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from app.config import config
from app.emails.blocked.excluded_emails import excluded_email
from app.http_client import http_client
from app.launchpad.cookies import (
    LaunchpadAccessTokenCookieSession,
    LaunchpadPendingAuthCookieSession,
    launchpad_access_token_cookie_session,
    launchpad_pending_auth_cookie_session,
)
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
from app.utils.request import update_query_params

logger = logging.getLogger(__name__)


class LaunchpadService:
    """
    Launchpad OAuth service.
    Docs: https://help.launchpad.net/API/SigningRequests
    """

    def __init__(
        self,
        pending_auth_cookie_session: LaunchpadPendingAuthCookieSession,
        access_token_cookie_session: LaunchpadAccessTokenCookieSession,
        http_client: httpx.AsyncClient,
    ):
        self.pending_auth_cookie_session = pending_auth_cookie_session
        self.access_token_cookie_session = access_token_cookie_session
        self.http_client = http_client

    async def login(self, callback_url: str, redirect_url: str) -> RedirectResponse:
        """Redirect to Launchpad OAuth login page."""
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
        try:
            request_token_response = LaunchpadRequestTokenResponse.model_validate(
                response.json()
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate request token response from Launchpad: {e}",
            ) from e
        state = secrets.token_urlsafe(16)
        authorize_token_params = urlencode(
            {
                "oauth_token": request_token_response.oauth_token,
                "oauth_callback": f"{callback_url}?state={state}",
                "allow_permission": "READ_PRIVATE",
            }
        )

        response = RedirectResponse(
            url=f"https://launchpad.net/+authorize-token?{authorize_token_params}"
        )
        request_token_session = RequestTokenSession(
            oauth_token=request_token_response.oauth_token,
            oauth_token_secret=request_token_response.oauth_token_secret,
            state=state,
            redirect_url=redirect_url,
        )
        self.pending_auth_cookie_session.set_cookie(
            response,
            value=request_token_session,
            max_age=600,
        )
        return response

    async def callback(
        self,
        oauth_token: str,
        oauth_token_secret: str,
        redirect_url: str,
    ) -> RedirectResponse:
        """Exchange request token for access token."""
        access_token_params = {
            "oauth_consumer_key": config.app_name,
            "oauth_token": oauth_token,
            "oauth_signature_method": "PLAINTEXT",
            "oauth_signature": f"&{oauth_token_secret}",
        }
        response = await self.http_client.post(
            "https://launchpad.net/+access-token",
            data=access_token_params,
        )
        response_body = response.text
        if response.status_code != 200 or not response_body:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get access token from Launchpad: {response_body}",
            )
        try:
            # Launchpad API returns application/x-www-form-urlencoded so we need to parse the response body
            parsed_response_body = dict(
                parse_qsl(response_body, keep_blank_values=True)
            )
            access_token_response = LaunchpadAccessTokenResponse.model_validate(
                parsed_response_body
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate access token response from Launchpad: {e}",
            ) from e

        access_token_session = AccessTokenSession(
            oauth_token=access_token_response.oauth_token,
            oauth_token_secret=access_token_response.oauth_token_secret,
        )
        # XXX: This is a hack to get the access token into the redirect URL
        # Remove this once we migrate the CLA form over to this domain
        if not redirect_url.startswith(config.app_url):
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

    async def profile(
        self, access_token_session: AccessTokenSession
    ) -> LaunchpadProfile:
        # Get user profile
        response = await self.http_client.get(
            "https://api.launchpad.net/1.0/people/+me",
            follow_redirects=True,
            headers=self.authorization_header(access_token_session),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user data from Launchpad",
            )
        try:
            launchpad_user_profile = LaunchpadPersonResponse.model_validate(
                response.json()
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate user data from Launchpad: {e}",
            ) from e

        # Get primary email
        response = await self.http_client.get(
            url=launchpad_user_profile.preferred_email_address_link,
            follow_redirects=True,
            headers=self.authorization_header(access_token_session),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user primary email from Launchpad",
            )
        try:
            primary_email = LaunchpadEmailResponse.model_validate(response.json()).email
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate primary email from Launchpad: {e}",
            ) from e

        # Get additional emails (returns empty list if no additional emails)
        # TODO: check if people reach pagination limit, which is highly unlikely
        response = await self.http_client.get(
            url=launchpad_user_profile.confirmed_email_addresses_collection_link,
            follow_redirects=True,
            headers=self.authorization_header(access_token_session),
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get user emails from Launchpad",
            )
        try:
            email_list = LaunchpadEmailListResponse.model_validate(response.json())
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate email list from Launchpad: {e}",
            ) from e
        additional_emails = [entry.email for entry in email_list.entries]

        all_emails = [primary_email, *additional_emails]
        all_emails = [email for email in all_emails if not excluded_email(email)]
        return LaunchpadProfile(
            _id=str(launchpad_user_profile.id),
            username=launchpad_user_profile.name,
            emails=all_emails,
        )

    def authorization_header(
        self, access_token_session: AccessTokenSession
    ) -> dict[str, str]:
        return {
            "Authorization": ",".join(
                [
                    'OAuth realm="https://api.launchpad.net/"',
                    f'oauth_consumer_key="{config.app_name}"',
                    f'oauth_token="{access_token_session.oauth_token}"',
                    'oauth_signature_method="PLAINTEXT"',
                    f'oauth_signature="&{access_token_session.oauth_token_secret}"',
                    f"oauth_timestamp={int(time.time())}",
                    f"oauth_nonce={secrets.randbelow(2**50)}",
                    'oauth_version="1.0"',
                ]
            )
        }

    def logout(self, redirect_url: str | None) -> RedirectResponse | JSONResponse:
        """Clears the Launchpad session cookie."""
        response: RedirectResponse | JSONResponse
        if redirect_url:
            response = RedirectResponse(url=redirect_url)
        else:
            response = JSONResponse(
                content={
                    "message": "Logged out",
                    "login_url": f"{config.app_url}/launchpad/login",
                }
            )
        response.delete_cookie(key=self.access_token_cookie_session.name)
        return response


async def launchpad_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> LaunchpadService:
    return LaunchpadService(
        http_client=http_client,
        pending_auth_cookie_session=launchpad_pending_auth_cookie_session,
        access_token_cookie_session=launchpad_access_token_cookie_session,
    )


async def optional_launchpad_user(
    launchpad_access_token_session: AccessTokenSession | None = Depends(
        launchpad_access_token_cookie_session
    ),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
) -> LaunchpadProfile | None:
    if launchpad_access_token_session is None:
        return None
    return await launchpad_service.profile(
        access_token_session=launchpad_access_token_session
    )


async def launchpad_user(
    launchpad_access_token_session: AccessTokenSession | None = Depends(
        launchpad_access_token_cookie_session
    ),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
) -> LaunchpadProfile:
    user = await optional_launchpad_user(
        launchpad_access_token_session, launchpad_service
    )
    if user is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Launchpad access token is missing"
        )
    return user
