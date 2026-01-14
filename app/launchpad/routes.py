import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse, Response
from typing_extensions import TypedDict

from app.config import config
from app.launchpad.models import (
    AccessTokenSession,
    LaunchpadProfile,
    RequestTokenSession,
)
from app.launchpad.service import (
    LaunchpadService,
    launchpad_cookie_session,
    launchpad_service,
)
from app.utils import Base64, error_status_codes, update_query_params

launchpad_router = APIRouter(prefix="/launchpad", tags=["Launchpad"])


@launchpad_router.get(
    "/login",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/callback"]}),
)
async def launchpad_login(
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful login (base64 encoded).",
        ),
    ] = None,
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    """
    Redirects to Launchpad OAuth login page.
    """
    redirect_url_decoded = str(Base64.decode(redirect_url)) if redirect_url else None
    return await launchpad_service.login(
        callback_url=f"{config.app_url}/launchpad/callback",
        redirect_url=redirect_url_decoded,
    )


@launchpad_router.get(
    "/callback",
    status_code=307,
    response_model=TypedDict("Redirection", {"location": Literal["/profile"]}),
    responses=error_status_codes([401]),
)
async def launchpad_callback(
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
    redirect_url = session_data.get("redirect_url")
    try:
        access_token = await launchpad_service.callback(session_data=session_data)
    except HTTPException as e:
        if redirect_url:
            redirect_url = update_query_params(redirect_url, launchpad_error=e.detail)
            return RedirectResponse(url=redirect_url)
        else:
            raise e

    encrypted_access_token = launchpad_service.encrypt(json.dumps(access_token))

    if redirect_url:
        redirect_url = update_query_params(
            redirect_url, access_token=encrypted_access_token
        )
    else:
        redirect_url = f"{config.app_url}/launchpad/profile"

    redirect_response = RedirectResponse(url=redirect_url)
    launchpad_cookie_session.set_cookie(
        redirect_response,
        value=json.dumps(access_token),
        httponly=True,
    )
    return redirect_response


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
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful logout (base64 encoded).",
        ),
    ] = None,
) -> TypedDict("LogoutResponse", {"message": str, "login_url": str}):
    """
    Clears the Launchpad session.
    """
    response: Response
    if redirect_url:
        redirect_url_decoded = str(Base64.decode(redirect_url))
        response = RedirectResponse(url=redirect_url_decoded)
    else:
        response = JSONResponse(
            content={
                "message": "Logged out",
                "login_url": f"{config.app_url}/launchpad/login",
            }
        )
    response.delete_cookie(launchpad_cookie_session.model.name)
    return response
