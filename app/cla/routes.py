from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.responses import JSONResponse

from app.cla.models import (
    IndividualCreateForm,
    IndividualCreationSuccess,
    OrganizationCreationSuccess,
    OrganizationCreateForm,
)
from app.cla.service import CLAService, cla_service
from app.github.service import github_cookie_session
from app.launchpad.service import (
    launchpad_cookie_session,
)

cla_router = APIRouter(prefix="/cla", tags=["CLA"])


@cla_router.get(
    "/check",
    openapi_extra={
        "summary": "Check CLA",
    },
    responses={
        200: {
            "description": "Check CLA response",
            "content": {
                "application/json": {
                    "example": {
                        "dev1@ubuntu.com": True,
                        "dev2@example.com": False,
                    }
                }
            },
        }
    },
)
async def check_cla(
    emails: Annotated[
        list[str],
        Query(
            title="Emails",
            description="A list of emails to check for CLA signatories",
            max_length=100,
            examples=["dev1@ubuntu.com,dev2@example.com"],
        ),
    ],
    cla_service: CLAService = Depends(cla_service),
) -> dict[str, bool]:
    """
    Checks if one or multiple contributors have signed the CLA.
    """
    return await cla_service.check_cla(emails)


@cla_router.post(
    "/individual/sign",
    openapi_extra={"summary": "Sign Individual CLA"},
    status_code=201,
    response_model=IndividualCreationSuccess,
)
async def sign_cla_individual(
    individual: IndividualCreateForm,
    gh_session: str = Depends(github_cookie_session),
    lp_session: str = Depends(launchpad_cookie_session),
    cla_service: CLAService = Depends(cla_service),
):
    """
    Signs the CLA as an individual contributor.

    __Note:__
    The user must have a valid `github_oauth2_session` and `launchpad_oauth_session` cookie sessions in order to verify their email addresses.
    """
    await cla_service.individual_cla_sign(individual, gh_session, lp_session)
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
    cla_service: CLAService = Depends(cla_service),
):
    """
    Signs the CLA as an organization, representing a group of contributors.

    CLA check is based on the provided email domain, where a contributor
    GitHub or Launchpad email must match the email domain.
    """
    await cla_service.organization_cla_sign(organization)
    return JSONResponse(
        status_code=201, content=OrganizationCreationSuccess().model_dump()
    )
