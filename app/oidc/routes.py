from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.responses import Response
from typing_extensions import TypedDict

from app.config import config
from app.oidc.models import OIDCProfile
from app.oidc.service import (
    OIDCCookieSession,
    OIDCService,
    oidc_cookie_session,
    oidc_service,
)
from app.utils import Base64, error_status_codes, update_query_params

oidc_router = APIRouter(prefix="/oidc", tags=["Canonical OIDC"])


def check_oidc_enabled():
    if not config.canonical_oidc.enabled:
        raise HTTPException(status_code=503, detail="Canonical OIDC is not enabled")


@oidc_router.get(
    "/login",
    status_code=307,
    dependencies=[Depends(check_oidc_enabled)],
    openapi_extra={"summary": "Login to Canonical OIDC"},
)
async def oidc_login(
    redirect_url: Annotated[
        str | None,
        Query(
            description="URL to redirect to after login (base64 encoded).",
            examples=["aHR0cHM6Ly9leGFtcGxlLmNvbS9kYXNoYm9hcmQ="],
        ),
    ] = None,
    oidc_service: OIDCService = Depends(oidc_service),
) -> RedirectResponse:
    """Redirects to Canonical OIDC login page."""
    return await oidc_service.login(
        callback_url=f"{config.app_url}/oidc/callback",
        redirect_url=Base64.decode(redirect_url) if redirect_url else None,
    )


@oidc_router.get(
    "/callback",
    status_code=307,
    responses=error_status_codes([400, 401]),
    dependencies=[Depends(check_oidc_enabled)],
    openapi_extra={"summary": "Callback from Canonical OIDC"},
)
async def oidc_callback(
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query(include_in_schema=False)] = None,
    oidc_session: OIDCCookieSession | None = Depends(oidc_cookie_session),
    oidc_service: OIDCService = Depends(oidc_service),
) -> RedirectResponse:
    """Handles the Canonical OIDC callback."""
    if oidc_session is None or not code or not state:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: OIDC session missing, please login first",
        )
    if state != oidc_session["state"]:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state mismatch"
        )

    redirect_url = oidc_session.get("redirect_url")

    if error_description:
        if redirect_url:
            return RedirectResponse(
                url=update_query_params(redirect_url, oidc_error=error_description)
            )
        raise HTTPException(status_code=400, detail=f"OIDC Error: {error_description}")

    try:
        access_token = await oidc_service.callback(
            code, f"{config.app_url}/oidc/callback"
        )
    except HTTPException as e:
        if redirect_url:
            return RedirectResponse(
                url=update_query_params(redirect_url, oidc_error=e.detail)
            )
        raise

    encrypted_token = oidc_service.encrypt(access_token)
    redirect_url = (
        update_query_params(redirect_url, access_token=encrypted_token)
        if redirect_url
        else f"{config.app_url}/oidc/profile"
    )

    response = RedirectResponse(url=redirect_url)
    oidc_cookie_session.set_cookie(
        response,
        value=access_token,
        httponly=True,
        secure=not config.debug_mode,
        samesite="lax",
    )
    return response


@oidc_router.get(
    "/profile",
    responses=error_status_codes([401, 503]),
    dependencies=[Depends(check_oidc_enabled)],
    openapi_extra={"summary": "Profile from Canonical OIDC"},
)
async def oidc_profile(
    access_token: str | None = Depends(oidc_cookie_session),
    oidc_service: OIDCService = Depends(oidc_service),
) -> OIDCProfile:
    """Retrieves the OIDC profile of the authenticated user."""
    if access_token is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OIDC access token missing"
        )
    return await oidc_service.profile(access_token)


@oidc_router.get(
    "/logout",
    dependencies=[Depends(check_oidc_enabled)],
    openapi_extra={"summary": "Logout from Canonical OIDC"},
)
async def oidc_logout(
    redirect_url: Annotated[
        str | None,
        Query(description="URL to redirect to after logout (base64 encoded)."),
    ] = None,
) -> TypedDict("LogoutResponse", {"message": str, "login_url": str}):
    """Clears the OIDC session cookie."""
    response: Response
    if redirect_url:
        response = RedirectResponse(url=Base64.decode(redirect_url))
    else:
        response = JSONResponse(
            content={
                "message": "Logged out",
                "login_url": f"{config.app_url}/oidc/login",
            }
        )
    response.delete_cookie(oidc_cookie_session.model.name)
    return response
