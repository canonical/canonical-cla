from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.requests import Request
from starlette.responses import Response
from typing_extensions import TypedDict

from app.config import config
from app.github.models import GithubProfile, GitHubWebhookPayload
from app.github.service import GithubService, github_cookie_session, github_service
from app.github.webhook_service import GithubWebhookService, github_webhook_service
from app.utils import Base64, error_status_codes, update_query_params

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
    return await github_service.login(
        f"{config.app_url}/github/callback",
        redirect_url=Base64.decode(redirect_url) if redirect_url else None,
    )


@github_router.get(
    "/callback",
    status_code=307,
    responses=error_status_codes([400, 401]),
)
async def github_callback(
    code: Annotated[
        str | None,
        Query(
            description="The OAuth code returned by GitHub.",
            examples=["df45d15568265833c19a"],
        ),
    ] = None,
    state: Annotated[
        str | None,
        Query(
            description="A security check state.", examples=["vgdC38-XOeSIDXImpHnrHQ"]
        ),
    ] = None,
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
    if github_session is None or not code or not state:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: GitHub session is missing please login first",
        )
    session_state = github_session["state"]
    if state != session_state:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state does not match"
        )

    redirect_url = github_session.get("redirect_url")
    if error_description:
        if redirect_url:
            redirect_url = update_query_params(
                redirect_url, github_error=error_description
            )
            return RedirectResponse(url=redirect_url)
        else:
            raise HTTPException(
                status_code=400, detail=f"Bad Request: {error_description}"
            )

    try:
        github_access_token = await github_service.callback(
            code,
        )
    except HTTPException as e:
        if redirect_url:
            redirect_url = update_query_params(redirect_url, github_error=e.detail)
            return RedirectResponse(url=redirect_url)
        else:
            raise e

    encrypted_access_token = github_service.encrypt(github_access_token)
    if redirect_url:
        redirect_url = update_query_params(
            redirect_url, access_token=encrypted_access_token
        )
    else:
        redirect_url = f"{config.app_url}/github/profile"
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
        redirect_url = Base64.decode(redirect_url)
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


@github_router.post("/webhook", responses=error_status_codes([403]))
async def webhook(
    request: Request,
    github_webhook_service: GithubWebhookService = Depends(github_webhook_service),
) -> TypedDict("WebhookResponse", {"message": str}):
    """
    Handles GitHub webhooks.

    This endpoint should be used as the webhook URL when creating a GitHub App.
    The GitHub App must have the following permissions:
    - **Pull Requests**: `Read-only`
    - **Checks**: `Read & write`

    And be subscribed to the following events:
    - `Pull request`
    - `Check run`
    """
    payload_body = await request.body()
    signature_header = request.headers.get("x-hub-signature-256")
    github_webhook_service.verify_signature(payload_body, signature_header)

    payload = GitHubWebhookPayload.model_validate(await request.json())
    return await github_webhook_service.process_webhook(payload)
