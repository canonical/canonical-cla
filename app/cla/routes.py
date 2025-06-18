from asyncio import sleep
from datetime import datetime
from pathlib import Path
from typing import Annotated, List
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse

from app.cla.models import (
    CLACheckResponse,
    IndividualCreateForm,
    IndividualCreationSuccess,
    OrganizationCreateForm,
    OrganizationCreationSuccess,
)
from app.cla.service import CLAService, cla_service
from app.config import config
from app.github.service import github_cookie_session
from app.launchpad.service import launchpad_cookie_session
from app.notifications.emails import (
    send_individual_confirmation_email,
    send_legal_notification,
    send_organization_confirmation_email,
    send_organization_deleted,
    send_organization_status_update,
)
from app.repository.organization import OrganizationRepository, organization_repository
from app.utils import AESCipher, cipher

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

cla_router = APIRouter(prefix="/cla", tags=["CLA"])


@cla_router.get(
    "/check",
    openapi_extra={
        "summary": "Check CLA",
    },
)
async def check_cla(
    emails: List[str] | None = Query(
        title="Emails",
        description="A list of emails to check for CLA signatories",
        max_length=100,
        examples=["dev1@ubuntu.com,dev2@example.com"],
        default=[],
    ),
    github_usernames: List[str] | None = Query(
        title="GitHub Usernames",
        description="A list of GitHub usernames to check for CLA signatories",
        max_length=100,
        examples=["dev1,dev2"],
        default=[],
    ),
    launchpad_usernames: List[str] | None = Query(
        title="Launchpad Usernames",
        description="A list of Launchpad usernames to check for CLA signatories",
        max_length=100,
        examples=["dev1,dev2"],
        default=[],
    ),
    cla_service: CLAService = Depends(cla_service),
) -> CLACheckResponse:
    """
    Checks if one or multiple contributors have signed the CLA.
    """
    return await cla_service.check_cla(emails, github_usernames, launchpad_usernames)


@cla_router.post(
    "/individual/sign",
    openapi_extra={"summary": "Sign Individual CLA"},
    status_code=201,
    response_model=IndividualCreationSuccess,
)
async def sign_cla_individual(
    individual: IndividualCreateForm,
    background_tasks: BackgroundTasks,
    cla_service: CLAService = Depends(cla_service),
    gh_session: str | None = Depends(github_cookie_session),
    lp_session: dict | None = Depends(launchpad_cookie_session),
):
    """
    Signs the CLA as an individual contributor.

    __Note:__
    The user must have a valid `github_oauth2_session` and `launchpad_oauth_session` cookie sessions in order to verify their email addresses.
    """
    if config.maintenance_mode:
        raise HTTPException(
            status_code=503,
            detail="Canonical CLA is currently under maintenance. Please try again later.",
        )
    created_individual = await cla_service.individual_cla_sign(
        individual, gh_session, lp_session
    )

    for email in {created_individual.github_email, created_individual.launchpad_email}:
        if email:
            background_tasks.add_task(
                send_individual_confirmation_email,
                email,
                created_individual.first_name + " " + created_individual.last_name,
            )
    return JSONResponse(
        status_code=201, content=IndividualCreationSuccess().model_dump()
    )


@cla_router.post(
    "/organization/sign",
    openapi_extra={"summary": "Sign Organization CLA"},
    status_code=201,
    response_model=OrganizationCreationSuccess,
)
async def sign_cla_organization(
    organization: OrganizationCreateForm,
    background_tasks: BackgroundTasks,
    cla_service: CLAService = Depends(cla_service),
    cipher: AESCipher = Depends(cipher),
    gh_session: str | None = Depends(github_cookie_session),
    lp_session: dict | None = Depends(launchpad_cookie_session),
):
    """
    Signs the CLA as an organization, representing a group of contributors.

    CLA check is based on the provided email domain, where a contributor
    GitHub or Launchpad email must match the email domain.
    """
    if config.maintenance_mode:
        raise HTTPException(
            status_code=503,
            detail="Canonical CLA is currently under maintenance. Please try again later.",
        )
    created_organization = await cla_service.organization_cla_sign(
        organization, gh_session, lp_session
    )
    manage_organization_url = list(
        urlparse(urljoin(config.app_url, "/cla/organization"))
    )
    manage_organization_url[4] = urlencode(
        {"id": cipher.encrypt(str(created_organization.id))}
    )

    background_tasks.add_task(
        send_legal_notification,
        created_organization.name,
        created_organization.contact_name,
        created_organization.contact_email,
        created_organization.phone_number,
        created_organization.address,
        created_organization.country,
        created_organization.email_domain,
        urlunparse(manage_organization_url),
    )
    background_tasks.add_task(
        send_organization_confirmation_email,
        created_organization.contact_email,
        created_organization.contact_name,
        created_organization.name,
        created_organization.email_domain,
    )

    return JSONResponse(
        status_code=201, content=OrganizationCreationSuccess().model_dump()
    )


@cla_router.get("/organization", include_in_schema=False)
async def manage_organization(
    request: Request,
    id: str,
    message: str | None = None,
    email_sent: bool | None = None,
    organization_repository: OrganizationRepository = Depends(
        organization_repository),
    cipher: AESCipher = Depends(cipher),
):
    """
    Manage the organization CLA.
    """
    decrypted_organization_id = cipher.decrypt(id)

    if not decrypted_organization_id:
        # make it annoyingly slow to avoid this behavior
        await sleep(10)
        raise HTTPException(status_code=404, detail="Organization not found")
    organization = await organization_repository.get_organization_by_id(
        int(decrypted_organization_id)
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return templates.TemplateResponse(
        request=request,
        name="manage_organization.j2",
        context={
            "organization_id": id,
            "organization": organization.as_dict(),
            "message": message,
            "email_sent": email_sent,
        },
    )


@cla_router.post("/organization", include_in_schema=False)
async def update_organization(
    background_tasks: BackgroundTasks,
    id: str,
    email_domain: Annotated[str, Form()],
    salesforce_url: Annotated[str | None, Form()] = None,
    approved: Annotated[str | None, Form()] = None,
    organization_repository: OrganizationRepository = Depends(
        organization_repository),
    cipher: AESCipher = Depends(cipher),
):
    """
    Update the organization CLA.
    """
    decrypted_organization_id = cipher.decrypt(id)
    if not decrypted_organization_id:
        await sleep(10)
        raise HTTPException(status_code=404, detail="Organization not found")

    organization = await organization_repository.get_organization_by_id(
        int(decrypted_organization_id)
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization.email_domain = email_domain
    organization.salesforce_url = salesforce_url

    approved = approved == "on"
    current_approved_status = organization.is_active()
    if approved:
        if not organization.signed_at:
            organization.signed_at = datetime.now()
        if organization.revoked_at:
            organization.revoked_at = None
    else:
        organization.revoked_at = datetime.now()
    await organization_repository.update_organization(organization)
    email_sent = False
    if current_approved_status != approved:
        email_sent = True
        background_tasks.add_task(
            send_organization_status_update,
            organization.contact_email,
            organization.contact_name,
            organization.name,
            "approved" if approved else "disabled",
            organization.email_domain,
        )

    url = list(urlparse(f"{config.app_url}/cla/organization"))
    url[4] = urlencode(
        {
            "id": id,
            "message": "Organization updated successfully",
            "email_sent": email_sent,
        }
    )
    return RedirectResponse(urlunparse(url), status_code=302)


@cla_router.get("/organization/delete", include_in_schema=False)
async def delete_organization(
    request: Request,
    background_tasks: BackgroundTasks,
    id: str,
    organization_repository: OrganizationRepository = Depends(
        organization_repository),
    cipher: AESCipher = Depends(cipher),
):
    """
    Delete the organization CLA.
    """
    decrypted_organization_id = cipher.decrypt(id)
    print(decrypted_organization_id)
    if not decrypted_organization_id:
        await sleep(10)
        raise HTTPException(status_code=404, detail="Organization not found")
    organization = await organization_repository.get_organization_by_id(
        int(decrypted_organization_id)
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization = await organization_repository.delete_organization(organization)
    background_tasks.add_task(
        send_organization_deleted,
        organization.contact_email,
        organization.contact_name,
        organization.name,
    )
    return templates.TemplateResponse(
        request=request,
        name="deleted_organization.j2",
        context={
            "organization_name": organization.name,
        },
    )
