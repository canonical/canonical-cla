from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from app.config import config
from app.github.cookies import github_pending_auth_cookie_session
from app.github.models import (
    GithubPendingAuthSession,
    GitHubProfile,
    GitHubWebhookPayload,
)
from app.github.service import GithubService, github_service, github_user
from app.github.webhook_service import GithubWebhookService, github_webhook_service
from app.utils.base64 import Base64
from app.utils.open_redirects import validate_open_redirect
from app.utils.request import error_status_codes, update_query_params

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
):
    """
    Redirects to GitHub OAuth login page.
    """
    decoded_redirect_url = Base64.decode_str(redirect_url) if redirect_url else None
    if decoded_redirect_url:
        validate_open_redirect(decoded_redirect_url)
    return await github_service.login(
        f"{config.app_url}/github/callback",
        redirect_url=decoded_redirect_url or f"{config.app_url}/github/profile",
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
    github_pending_auth_session: GithubPendingAuthSession | None = Depends(
        github_pending_auth_cookie_session
    ),
    github_service: GithubService = Depends(github_service),
) -> RedirectResponse:
    """
    Handles the GitHub OAuth callback.
    """
    if github_pending_auth_session is None or not code or not state:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: GitHub session is missing please login first",
        )
    if state != github_pending_auth_session.state:
        raise HTTPException(
            status_code=401, detail="Unauthorized: OAuth state does not match"
        )

    redirect_url = github_pending_auth_session.redirect_url
    if error_description:
        if redirect_url != f"{config.app_url}/github/profile":
            redirect_url = update_query_params(
                redirect_url, github_error=error_description
            )
            return RedirectResponse(url=redirect_url)
        else:
            raise HTTPException(
                status_code=400, detail=f"Bad Request: {error_description}"
            )
    return await github_service.callback(
        code,
        redirect_url,
    )


@github_router.get("/profile", responses=error_status_codes([401]))
async def github_profile(
    github_user: GitHubProfile = Depends(github_user),
) -> GitHubProfile:
    """
    Retrieves the GitHub profile of the authenticated user.
    """
    return github_user


@github_router.get("/logout")
async def github_logout(
    redirect_url: Annotated[
        str | None,
        Query(
            description="The URL to redirect to after successful logout (base64 encoded).",
            examples=["https://example.com/form?a=1&b=2"],
        ),
    ] = None,
    github_service: GithubService = Depends(github_service),
):
    """
    Clears the GitHub session cookie.
    """
    decoded_redirect_url = Base64.decode_str(redirect_url) if redirect_url else None
    if decoded_redirect_url:
        validate_open_redirect(decoded_redirect_url)
    return github_service.logout(decoded_redirect_url)


@github_router.post("/webhook", responses=error_status_codes([400, 403]))
async def webhook(
    request: Request,
    github_webhook_service: GithubWebhookService = Depends(github_webhook_service),
):
    """
    Handles GitHub webhooks.

    This endpoint should be used as the webhook URL when creating a GitHub App.
    The GitHub App must have the following permissions:
    - **Pull Requests**: `Read-only`
    - **Contents**: `Read-only` (required for private repositories)
    - **Checks**: `Read & write`

    And be subscribed to the following events:
    - `Pull request`
    - `Check run`
    """
    payload_body = await request.body()
    signature_header = request.headers.get("x-hub-signature-256")
    github_webhook_service.verify_signature(payload_body, signature_header)

    try:
        payload = GitHubWebhookPayload.model_validate(await request.json())
    except Exception as e:
        from pydantic_core import _pydantic_core

        if isinstance(e, _pydantic_core.ValidationError):
            raise HTTPException(status_code=400, detail="Invalid webhook payload")
        raise
    return await github_webhook_service.process_webhook(payload)
