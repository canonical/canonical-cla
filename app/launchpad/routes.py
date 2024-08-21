import base64
import json
from typing import Annotated, Literal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse, Response
from typing_extensions import TypedDict

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
    if redirect_url:
        redirect_url = base64.b64decode(redirect_url).decode("utf-8")

    return await launchpad_service.login(
        callback_url=request.url_for("launchpad_callback")._url,
        success_redirect_url=redirect_url or request.url_for("launchpad_profile")._url,
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
    access_token = await launchpad_service.callback(
        profile_url=request.url_for("launchpad_profile")._url, session_data=session_data
    )

    encrypted_access_token = launchpad_service.encrypt(json.dumps(access_token))

    redirect_url_parts = list(urlparse(launchpad_session["success_redirect_url"]))
    query = dict(parse_qsl(redirect_url_parts[4]))
    query["access_token"] = encrypted_access_token
    redirect_url_parts[4] = urlencode(query)
    redirect_url = urlunparse(redirect_url_parts)

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
    request: Request,
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
        redirect_url = base64.b64decode(redirect_url).decode("utf-8")
        response = RedirectResponse(url=redirect_url)
    else:
        response = JSONResponse(
            content={
                "message": "Logged out",
                "login_url": request.url_for("launchpad_login")._url,
            }
        )
    response.delete_cookie(launchpad_cookie_session.model.name)
    return response
