import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.github.service import GithubService, github_cookie_session, github_service

github_router = APIRouter(prefix="/github")


@github_router.get("/login")
async def github_login(
    request: Request, github_service: GithubService = Depends(github_service)
):
    return await github_service.login(request.url_for("github_callback"))


@github_router.get("/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error_description: str | None = None,
    github_session: str | None = Depends(github_cookie_session),
    github_service: GithubService = Depends(github_service),
):
    if error_description:
        raise HTTPException(status_code=400, detail=f"Bad Request: {error_description}")
    if code is None or state is None or github_session is None:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth code or state are missing"
        )
    session_state = json.loads(github_session)["state"]
    if state != session_state:
        raise HTTPException(
            status_code=400, detail="Bad Request: OAuth state does not match"
        )
    return await github_service.callback(code, request.url_for("github_emails"))


@github_router.get("/emails")
async def github_emails(
    access_token: str | None = Depends(github_cookie_session),
    github_service: GithubService = Depends(github_service),
):
    if access_token is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: GitHub Access token is missing"
        )
    return await github_service.emails(access_token)


@github_router.get("/github/logout")
async def github_logout(
    request: Request,
):
    response = JSONResponse(
        content={
            "message": "Logged out",
            "login_url": request.url_for("github_login")._url,
        }
    )
    response.delete_cookie(github_cookie_session.model.name)
    return response
