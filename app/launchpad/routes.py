from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from typing_extensions import TypedDict

from app.config import config
from app.launchpad.cookies import launchpad_pending_auth_cookie_session
from app.launchpad.models import LaunchpadProfile, RequestTokenSession
from app.launchpad.service import LaunchpadService, launchpad_service, launchpad_user
from app.utils.base64 import Base64
from app.utils.open_redirects import validate_open_redirect
from app.utils.request import error_status_codes

launchpad_router = APIRouter(prefix="/launchpad", tags=["Launchpad"])


@launchpad_router.get(
    "/login",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/callback"]}),
)
async def launchpad_login(
    # deprecated parameter
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful login (base64 encoded).",
        ),
    ] = None,
    # new parameter
    redirect_uri: Annotated[
        str | None,
        Query(
            description="The redirect URI to redirect to after login.",
            examples=["/dashboard"],
        ),
    ] = None,
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """
    Redirects to Launchpad OAuth login page.
    """
    decoded_redirect_url = Base64.decode_str(redirect_url) if redirect_url else None
    if decoded_redirect_url:
        validate_open_redirect(decoded_redirect_url)
    return await launchpad_service.login(
        callback_url=f"{config.app_url}/launchpad/callback",
        redirect_url=f"{config.app_url}{redirect_uri}"
        or decoded_redirect_url
        or f"{config.app_url}/launchpad/profile",
    )


@launchpad_router.get(
    "/callback",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/profile"]}),
    responses=error_status_codes([401]),
)
async def launchpad_callback(
    state: Annotated[str, Query(description="The OAuth state returned by Launchpad.")],
    launchpad_session: Annotated[
        RequestTokenSession | None, Depends(launchpad_pending_auth_cookie_session)
    ],
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """
    Handles the Launchpad OAuth callback.
    """
    if launchpad_session is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth session is missing"
        )
    if state != launchpad_session.state:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state mismatch"
        )

    return await launchpad_service.callback(
        oauth_token=launchpad_session.oauth_token,
        oauth_token_secret=launchpad_session.oauth_token_secret,
        redirect_url=launchpad_session.redirect_url,
    )


@launchpad_router.get("/profile", responses=error_status_codes([401]))
async def launchpad_profile(
    launchpad_user: LaunchpadProfile = Depends(launchpad_user),
) -> LaunchpadProfile:
    """Retrieves the Launchpad profile of the authenticated user."""
    return launchpad_user


@launchpad_router.get("/logout")
async def launchpad_logout(
    # deprecated parameter
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful logout (base64 encoded).",
        ),
    ] = None,
    # new parameter
    redirect_uri: Annotated[
        str | None,
        Query(
            description="The redirect URI to redirect to after logout.",
            examples=["/dashboard"],
        ),
    ] = None,
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """Clears the Launchpad session cookie."""
    decoded_redirect_url = Base64.decode_str(redirect_url) if redirect_url else None
    if decoded_redirect_url:
        validate_open_redirect(decoded_redirect_url)
    return launchpad_service.logout(redirect_uri or decoded_redirect_url)
