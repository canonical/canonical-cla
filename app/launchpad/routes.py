from typing import Annotated, TypedDict, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from app.launchpad.models import (
    AccessTokenSession,
    RequestTokenSession,
    LaunchpadProfile,
)
from app.launchpad.service import (
    LaunchpadService,
    launchpad_cookie_session,
    launchpad_service,
)
from app.utils import error_status_codes

launchpad_router = APIRouter(prefix="/launchpad", tags=["Launchpad"])


@launchpad_router.get(
    "/login",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/callback"]}),
)
async def launchpad_login(
    request: Request,
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """
    Redirects to Launchpad OAuth login page.
    """
    return await launchpad_service.login(
        callback_url=request.url_for("launchpad_callback")._url
    )


@launchpad_router.get(
    "/callback",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/profile"]}),
    responses=error_status_codes([401]),
)
async def launchpad_callback(
    request: Request,
    state: Annotated[str, Query(description="The OAuth state returned by Launchpad.")],
    launchpad_session: dict | None = Depends(launchpad_cookie_session),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """
    Handles the Launchpad OAuth callback.
    """
    if launchpad_session is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth session is missing"
        )
    session_data = RequestTokenSession(**launchpad_session)
    if state != session_data["state"]:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state mismatch"
        )
    return await launchpad_service.callback(
        profile_url=request.url_for("launchpad_profile")._url, session_data=session_data
    )


@launchpad_router.get("/profile", responses=error_status_codes([401]))
async def launchpad_profile(
    launchpad_session: dict | None = Depends(launchpad_cookie_session),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
) -> LaunchpadProfile:
    """
    Fetches the Launchpad profile of the authenticated user.
    """
    if launchpad_session is None:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth session is missing"
        )
    session_data = AccessTokenSession(**launchpad_session)
    return await launchpad_service.profile(session_data=session_data)


@launchpad_router.get("/logout")
async def launchpad_logout(
    request: Request,
) -> TypedDict("LogoutResponse", {"message": str, "login_url": str}):
    """
    Clears the Launchpad session.
    """
    response = JSONResponse(
        content={
            "message": "Logged out",
            "login_url": request.url_for("launchpad_login")._url,
        }
    )
    response.delete_cookie(launchpad_cookie_session.model.name)
    return response
