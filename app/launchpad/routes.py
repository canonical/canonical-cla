import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.launchpad.service import LaunchpadService

logger = logging.getLogger(__name__)
launchpad_router = APIRouter(prefix="/launchpad")


@launchpad_router.get("/login")
async def launchpad_login(
    request: Request, lp_service: LaunchpadService = Depends(LaunchpadService)
):
    return lp_service.login_redirect(request)


@launchpad_router.get("/callback")
async def launchpad_callback(
    request: Request,
    request_token: str,
    session_tokens: str | None = Depends(
        LaunchpadService.launchpad_oauth_cookie_session()
    ),
    lp_service: LaunchpadService = Depends(LaunchpadService),
):
    if session_tokens is None:
        return HTTPException(status_code=401, detail="Unauthorized: No user session")
    try:
        decoded_session_tokens = json.loads(session_tokens)
    except ValueError as e:
        logger.error("Unable to decode user session %s", e)
        return HTTPException(
            status_code=500, detail="Internal Server Error: Unable to get user session"
        )
    try:
        return lp_service.login_callback(
            decoded_session_tokens,
            callback_token=request_token,
            whoami_url=request.url_for("launchpad_whoami"),
        )
    except ValueError as e:
        return HTTPException(status_code=400, detail=str(e))


@launchpad_router.get("/whoami")
async def launchpad_whoami(
    response: Response,
    session_tokens: str | None = Depends(
        LaunchpadService.launchpad_oauth_cookie_session()
    ),
    lp_service: LaunchpadService = Depends(LaunchpadService),
):

    if session_tokens is None:
        return HTTPException(status_code=401, detail="Unauthorized: No user session")

    try:
        decoded_session_tokens = json.loads(session_tokens)
    except json.JSONDecodeError:
        logger.error("Unable to decode user session")
        return HTTPException(
            status_code=500, detail="Internal Server Error: Unable to get user session"
        )

    user = lp_service.whoami(response, decoded_session_tokens)
    if user is None:
        return HTTPException(
            status_code=401, detail="Unauthorized: Invalid user session"
        )
    return user


@launchpad_router.get("/logout")
async def launchpad_logout(
    request: Request, lp_service: LaunchpadService = Depends(LaunchpadService)
):
    response = JSONResponse(
        content={
            "message": "Logged out",
            "login_url": request.url_for("launchpad_login")._url,
        }
    )
    lp_service.logout(response)
    return response
