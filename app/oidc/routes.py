from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import config
from app.oidc.models import OIDCPendingAuthSession, OIDCProfile, OIDCUserInfo
from app.oidc.service import (
    OIDCService,
    oidc_pending_auth_cookie_session,
    oidc_service,
    oidc_user,
)
from app.repository.user_role import UserRoleRepository, user_role_repository
from app.utils.request import error_status_codes

oidc_router = APIRouter(prefix="/oidc", tags=["Canonical OIDC"])


@oidc_router.get(
    "/login",
    status_code=307,
    openapi_extra={"summary": "Login to Canonical OIDC"},
)
async def oidc_login(
    redirect_uri: Annotated[
        str | None,
        Query(
            description="The redirect URI to redirect to after login.",
            examples=["/dashboard"],
        ),
    ] = None,
    oidc_service: OIDCService = Depends(oidc_service),
):
    """Redirects to Canonical OIDC login page."""
    return await oidc_service.login(
        callback_url=f"{config.app_url}/oidc/callback",
        redirect_uri=f"{config.app_url}{redirect_uri}"
        if redirect_uri
        else "/oidc/profile",
    )


@oidc_router.get(
    "/callback",
    status_code=307,
    responses=error_status_codes([400, 401]),
    openapi_extra={"summary": "Callback from Canonical OIDC"},
)
async def oidc_callback(
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query(include_in_schema=False)] = None,
    oidc_pending_auth_session: OIDCPendingAuthSession | None = Depends(
        oidc_pending_auth_cookie_session
    ),
    oidc_service: OIDCService = Depends(oidc_service),
):
    """Handles the Canonical OIDC callback."""
    if oidc_pending_auth_session is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: OIDC session missing, please login first",
        )
    if state != oidc_pending_auth_session.state:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state mismatch"
        )

    if error_description:
        raise HTTPException(status_code=400, detail=f"OIDC Error: {error_description}")
    if not code:
        raise HTTPException(status_code=400, detail="OIDC Error: Code is required")
    return await oidc_service.callback(
        code,
        f"{config.app_url}/oidc/callback",
        oidc_pending_auth_session.redirect_uri,
    )


@oidc_router.get(
    "/profile",
    responses=error_status_codes([401, 503]),
    openapi_extra={"summary": "Profile from Canonical OIDC"},
)
async def oidc_profile(
    oidc_user: OIDCUserInfo = Depends(oidc_user),
    user_role_repository: UserRoleRepository = Depends(user_role_repository),
) -> OIDCProfile:
    """Retrieves the OIDC profile of the authenticated user."""
    user_role = await user_role_repository.get_user_role(oidc_user.email)
    return OIDCProfile(user=oidc_user, role=user_role.role if user_role else None)


@oidc_router.get(
    "/logout",
    openapi_extra={"summary": "Logout from Canonical OIDC"},
)
async def oidc_logout(
    redirect_uri: Annotated[
        str | None,
        Query(description="The redirect URI to redirect to after logout."),
    ] = None,
    oidc_service: OIDCService = Depends(oidc_service),
):
    """Clears the OIDC session cookie."""
    return await oidc_service.logout(redirect_uri)
