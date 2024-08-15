import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.launchpad.models import AccessTokenSession, RequestTokenSession
from app.launchpad.service import (
    LaunchpadService,
    launchpad_cookie_session,
    launchpad_service,
)

launchpad_router = APIRouter(prefix="/launchpad")


@launchpad_router.get("/login")
async def launchpad_login(
    request: Request,
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):

    return await launchpad_service.login(
        callback_url=request.url_for("launchpad_callback")
    )


@launchpad_router.get("/callback")
async def launchpad_callback(
    request: Request,
    state: str | None = None,
    launchpad_session: str | None = Depends(launchpad_cookie_session),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    if state is None or launchpad_session is None:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth state is missing"
        )
    session_data = RequestTokenSession(**json.loads(launchpad_session))
    if state != session_data["state"]:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth state does not match"
        )
    return await launchpad_service.callback(
        emails_url=request.url_for("launchpad_emails"), session_data=session_data
    )


@launchpad_router.get("/emails")
async def launchpad_emails(
    launchpad_session: str | None = Depends(launchpad_cookie_session),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
):
    if launchpad_session is None:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth session is missing"
        )
    session_data = AccessTokenSession(**json.loads(launchpad_session))
    return await launchpad_service.emails(session_data=session_data)


@launchpad_router.get("/logout")
async def launchpad_logout(request: Request):
    response = JSONResponse(
        content={
            "message": "Logged out",
            "login_url": request.url_for("launchpad_login")._url,
        }
    )
    response.delete_cookie(launchpad_cookie_session.model.name)
    return response
