import json
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.config import config
from app.oidc.models import OIDCMetadata, OIDCProfile
from app.utils import EncryptedAPIKeyCookie, http_client

logger = logging.getLogger(__name__)


class OIDCCookieSession(EncryptedAPIKeyCookie):
    pass


oidc_cookie_session = OIDCCookieSession(
    name="canonical_oidc_session",
    secret=config.secret_key.get_secret_value(),
    auto_error=False,
)


class OIDCService:
    """
    Canonical OIDC service.
    Docs: https://login.canonical.com/.well-known/openid-configuration
    """

    def __init__(
        self, cookie_session: OIDCCookieSession, http_client: httpx.AsyncClient
    ):
        self.cookie_session = cookie_session
        self.http_client = http_client
        self._metadata: OIDCMetadata | None = None

    async def _get_metadata(self) -> OIDCMetadata:
        """Fetch and cache OIDC provider metadata."""
        if self._metadata is None:
            response = await self.http_client.get(config.canonical_oidc.discovery_url)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502, detail="Failed to fetch OIDC metadata"
                )
            self._metadata = response.json()
        return self._metadata

    async def login(
        self, callback_url: str, redirect_url: str | None
    ) -> RedirectResponse:
        """Redirect to OIDC authorization endpoint."""
        metadata = await self._get_metadata()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        params = urlencode(
            {
                "client_id": config.canonical_oidc.client_id,
                "response_type": "code",
                "scope": config.canonical_oidc.scope,
                "redirect_uri": callback_url,
                "state": state,
                "nonce": nonce,
            }
        )

        response = RedirectResponse(
            url=f"{metadata['authorization_endpoint']}?{params}"
        )
        self.cookie_session.set_cookie(
            response,
            value=json.dumps(
                {"state": state, "nonce": nonce, "redirect_url": redirect_url}
            ),
            max_age=600,
            httponly=True,
            secure=not config.debug_mode,
            samesite="lax",
        )
        return response

    async def callback(self, code: str, callback_url: str) -> str:
        """Exchange authorization code for access token."""
        metadata = await self._get_metadata()

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback_url,
            "client_id": config.canonical_oidc.client_id,
            "client_secret": config.canonical_oidc.client_secret.get_secret_value(),
        }

        response = await self.http_client.post(
            url=metadata["token_endpoint"],
            data=token_data,
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for token"
            )

        token_response = response.json()
        if "error" in token_response:
            raise HTTPException(
                status_code=400,
                detail=f"Token error: {token_response.get('error_description', token_response['error'])}",
            )

        return token_response["access_token"]

    async def profile(self, access_token: str) -> OIDCProfile:
        """Fetch user profile from OIDC userinfo endpoint."""
        metadata = await self._get_metadata()

        response = await self.http_client.get(
            url=metadata["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Failed to fetch user profile"
            )

        userinfo = response.json()
        return OIDCProfile(
            sub=userinfo["sub"],
            email=userinfo.get("email"),
            email_verified=userinfo.get("email_verified", False),
            name=userinfo.get("name"),
            username=userinfo.get("preferred_username"),
            picture=userinfo.get("picture"),
            given_name=userinfo.get("given_name"),
            family_name=userinfo.get("family_name"),
        )

    def encrypt(self, value: str) -> str:
        return self.cookie_session.cipher.encrypt(value)


async def oidc_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> OIDCService:
    return OIDCService(oidc_cookie_session, http_client)
