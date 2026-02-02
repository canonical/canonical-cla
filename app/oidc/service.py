import logging
import secrets
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from app.config import config
from app.http_client import http_client
from app.oidc.cookies import (
    OIDCAccessTokenCookieSession,
    OIDCPendingAuthCookieSession,
    oidc_access_token_cookie_session,
    oidc_pending_auth_cookie_session,
)
from app.oidc.models import (
    OIDCAccessTokenSession,
    OIDCMetadata,
    OIDCPendingAuthSession,
    OIDCTokenResponse,
    OIDCUserInfo,
)

logger = logging.getLogger(__name__)


class OIDCService:
    """
    Canonical OIDC service.
    Docs: https://login.canonical.com/.well-known/openid-configuration
    """

    def __init__(
        self,
        access_token_cookie_session: OIDCAccessTokenCookieSession,
        pending_auth_cookie_session: OIDCPendingAuthCookieSession,
        http_client: httpx.AsyncClient,
    ):
        self.access_token_cookie_session = access_token_cookie_session
        self.pending_auth_cookie_session = pending_auth_cookie_session
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
            try:
                self._metadata = OIDCMetadata.model_validate(response.json())
            except ValidationError as e:
                logger.error(f"Failed to validate OIDC metadata: {e}", exc_info=True)
                raise HTTPException(
                    status_code=502,
                    detail="Failed to validate OIDC metadata, please try again later",
                ) from e
        return self._metadata

    async def login(self, callback_url: str, redirect_uri: str) -> RedirectResponse:
        """Redirect to OIDC authorization endpoint."""
        validated_redirect_uri = self._relative_non_login_path(redirect_uri)
        if not validated_redirect_uri:
            raise HTTPException(
                status_code=400,
                detail="Invalid redirect_uri: login path is not allowed",
            )

        metadata = await self._get_metadata()
        state = secrets.token_urlsafe(32)
        params = urlencode(
            {
                "client_id": config.canonical_oidc.client_id,
                "response_type": "code",
                "scope": config.canonical_oidc.scope,
                "redirect_uri": callback_url,
                "state": state,
            }
        )

        response = RedirectResponse(url=f"{metadata.authorization_endpoint}?{params}")
        pending_auth_session = OIDCPendingAuthSession(
            state=state, redirect_uri=validated_redirect_uri
        )
        self.pending_auth_cookie_session.set_cookie(
            response,
            value=pending_auth_session,
            max_age=600,
            httponly=True,
            secure=not config.debug_mode,
            samesite="lax",
        )
        return response

    async def callback(
        self, code: str, callback_url: str, redirect_uri: str
    ) -> RedirectResponse:
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
            url=metadata.token_endpoint,
            data=token_data,
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange code for token: {response.text}",
            )

        token_response = response.json()
        if "error" in token_response:
            raise HTTPException(
                status_code=400,
                detail=f"Token error: {token_response.get('error_description', token_response['error'])}",
            )
        try:
            token_response_payload = OIDCTokenResponse.model_validate(token_response)
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate token response: {e}",
            ) from e
        response = RedirectResponse(url=redirect_uri)
        access_token_session = OIDCAccessTokenSession(
            access_token=token_response_payload.access_token
        )
        self.access_token_cookie_session.set_cookie(
            response,
            value=access_token_session,
            httponly=True,
            secure=not config.debug_mode,
            samesite="lax",
        )
        response.delete_cookie(key=self.pending_auth_cookie_session.name)
        return response

    async def profile(self, access_token: str) -> OIDCUserInfo:
        """Fetch user profile from OIDC userinfo endpoint."""
        metadata = await self._get_metadata()

        response = await self.http_client.get(
            url=metadata.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Failed to fetch user profile"
            )

        try:
            return OIDCUserInfo.model_validate(response.json())
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate user profile: {e}",
            ) from e

    async def logout(self, redirect_uri: str | None) -> RedirectResponse | JSONResponse:
        response: RedirectResponse | JSONResponse
        validated_redirect_uri = (
            self._relative_non_login_path(redirect_uri) if redirect_uri else None
        )
        if validated_redirect_uri:
            response = RedirectResponse(url=validated_redirect_uri)
        else:
            response = JSONResponse(
                content={
                    "message": "Logged out",
                    "login_url": f"{config.app_url}/oidc/login",
                }
            )
        response.delete_cookie(key=self.access_token_cookie_session.name)
        return response

    def _relative_non_login_path(self, path: str) -> str | None:
        """Extract the relative path and query string

        return None if the path ends with `/login`, else return the relative path and query string."""

        parsed = urlparse(path)
        rel_path_with_query = parsed.path or "/"
        if parsed.query:
            rel_path_with_query += "?" + parsed.query

        if rel_path_with_query.rstrip("/").endswith(
            "/login"
        ) or rel_path_with_query.rstrip("/").endswith("/logout"):
            return None
        return rel_path_with_query


async def oidc_service(
    http_client: httpx.AsyncClient = Depends(http_client),
) -> OIDCService:
    return OIDCService(
        oidc_access_token_cookie_session, oidc_pending_auth_cookie_session, http_client
    )


async def oidc_user(
    oidc_access_token_session: OIDCAccessTokenSession | None = Depends(
        oidc_access_token_cookie_session
    ),
    oidc_service: OIDCService = Depends(oidc_service),
) -> OIDCUserInfo:
    if oidc_access_token_session is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized(OIDC): Not authenticated"
        )
    return await oidc_service.profile(oidc_access_token_session.access_token)
