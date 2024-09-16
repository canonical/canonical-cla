import base64
from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.responses import Response
from typing_extensions import TypedDict

from app.config import config
from app.github.models import GithubProfile
from app.github.service import GithubService, github_cookie_session, github_service
from app.utils import error_status_codes

github_router = APIRouter(prefix="/github", tags=["GitHub"])


@github_router.get("/login", status_code=307)
async def github_login(
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful login (base64 encoded).",
            examples=["https://example.com/form?a=1&b=2"],
        ),
    ] = None,
    github_service: GithubService = Depends(github_service),
) -> RedirectResponse:
    """
    Redirects to GitHub OAuth login page.
    """
    if redirect_url:
        redirect_url = base64.b64decode(redirect_url).decode("utf-8")
    return await github_service.login(
        f"{config.app_url}/github/callback",
        success_redirect_url=redirect_url or f"{config.app_url}/github/profile",
    )


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
    if not github_session["success_redirect_url"]:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Success redirect URL is missing"
        )
    github_access_token = await github_service.callback(
        code,
    )
    encrypted_access_token = github_service.encrypt(github_access_token)

    redirect_url_parts = list(urlparse(github_session["success_redirect_url"]))
    query = dict(parse_qsl(redirect_url_parts[4]))
    query["access_token"] = encrypted_access_token
    redirect_url_parts[4] = urlencode(query)
    redirect_url = urlunparse(redirect_url_parts)

    redirect_response = RedirectResponse(url=redirect_url)
    github_cookie_session.set_cookie(
        redirect_response,
        value=github_access_token,
        httponly=True,
    )
    return redirect_response


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


@github_router.get("/logout")
async def github_logout(
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful logout (base64 encoded).",
            examples=["https://example.com/form?a=1&b=2"],
        ),
    ] = None,
) -> TypedDict("LogoutResponse", {"message": str, "login_url": str}):
    """
    Clears the GitHub session cookie.
    """
    response: Response
    if redirect_url:
        redirect_url = base64.b64decode(redirect_url).decode("utf-8")
        response = RedirectResponse(url=redirect_url)
    else:
        response = JSONResponse(
            content={
                "message": "Logged out",
                "login_url": f"{config.app_url}/github/login",
            }
        )
    response.delete_cookie(github_cookie_session.model.name)
    return response
