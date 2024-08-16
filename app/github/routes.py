from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse

from app.github.models import GithubProfile
from app.github.service import GithubService, github_cookie_session, github_service
from app.utils import error_status_codes

github_router = APIRouter(prefix="/github", tags=["GitHub"])


@github_router.get("/login", status_code=307)
async def github_login(
    request: Request, github_service: GithubService = Depends(github_service)
) -> RedirectResponse:
    """
    Redirects to GitHub OAuth login page.
    """
    return await github_service.login(request.url_for("github_callback")._url)


@github_router.get(
    "/callback",
    status_code=307,
    responses=error_status_codes([400, 401]),
)
async def github_callback(
    request: Request,
    code: Annotated[
        str,
        Query(
            description="The OAuth code returned by GitHub.",
            examples=["df45d15568265833c19a"],
        ),
    ],
    state: Annotated[
        str,
        Query(
            description="A security check state.", examples=["vgdC38-XOeSIDXImpHnrHQ"]
        ),
    ],
    error_description: Annotated[
        str | None,
        Query(
            include_in_schema=False,
        ),
    ] = None,
    github_session: dict | None = Depends(github_cookie_session),
    github_service: GithubService = Depends(github_service),
) -> RedirectResponse:
    """
    Handles the GitHub OAuth callback.
    """
    if error_description:
        raise HTTPException(status_code=400, detail=f"Bad Request: {error_description}")
    if github_session is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: GitHub session is missing please login first",
        )
    session_state = github_session["state"]
    if state != session_state:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state does not match"
        )
    return await github_service.callback(code, request.url_for("github_profile")._url)


@github_router.get("/profile", responses=error_status_codes([401]))
async def github_profile(
    access_token: str | None = Depends(github_cookie_session),
    github_service: GithubService = Depends(github_service),
) -> GithubProfile:
    """
    Retrieves the GitHub profile of the authenticated user.
    """
    if access_token is None:
        raise HTTPException(
            status_code=401, detail="Unauthorized: GitHub Access token is missing"
        )
    return await github_service.profile(access_token)


@github_router.get("/github/logout")
async def github_logout(
    request: Request,
) -> TypedDict("LogoutResponse", {"message": str, "login_url": str}):
    """
    Clears the GitHub session cookie.
    """
    response = JSONResponse(
        content={
            "message": "Logged out",
            "login_url": request.url_for("github_login")._url,
        }
    )
    response.delete_cookie(github_cookie_session.model.name)
    return response
