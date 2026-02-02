from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic_extra_types.country import CountryAlpha2

from app.cla.models import (
    CLACheckResponse,
    IndividualCreateForm,
    OrganizationCreateForm,
)
from app.cla.routes import (
    check_cla,
    manage_organization,
    sign_cla_individual,
    sign_cla_organization,
)
from app.github.models import GitHubProfile
from app.launchpad.models import LaunchpadProfile


@pytest.mark.asyncio
async def test_cla_check():
    cla_service = MagicMock()
    cla_service.check_cla = AsyncMock(
        return_value=CLACheckResponse(
            emails={"email1": True, "email2": False},
            github_usernames={"dev1": False, "dev2": True},
            launchpad_usernames={
                "lp_dev1": True,
                "dev1": False,
                "lp_dev2": True,
            },
        )
    )
    response = await check_cla(
        emails=["email1", "email2"],
        github_usernames=["dev1", "dev2"],
        launchpad_usernames=["lp_dev1", "dev1", "lp_dev2"],
        cla_service=cla_service,
    )

    assert response == cla_service.check_cla.return_value
    assert cla_service.check_cla.called


@pytest.mark.asyncio
async def test_sign_cla_individual():
    cla_service = MagicMock()
    cla_service.individual_cla_sign = AsyncMock()
    individual_form = IndividualCreateForm(
        first_name="test",
        last_name="test",
        address="address",
        country=CountryAlpha2("FR"),
        github_email="email1@email.com",
        launchpad_email="email2@email.com",
    )
    background_tasks = MagicMock()
    await sign_cla_individual(
        individual=individual_form,
        background_tasks=background_tasks,
        cla_service=cla_service,
        github_user=GitHubProfile(username="u", _id=1, emails=["email1@email.com"]),
        launchpad_user=LaunchpadProfile(
            username="u", _id="lp1", emails=["email2@email.com"]
        ),
    )

    assert cla_service.individual_cla_sign.called
    assert background_tasks.add_task.called


@pytest.mark.asyncio
async def test_sign_cla_organization():
    cla_service = MagicMock()
    cla_service.organization_cla_sign = AsyncMock()
    organization_form = OrganizationCreateForm(
        name="test",
        address="address",
        country=CountryAlpha2("FR"),
        phone_number="1234567890",
        email_domain="email.com",
        contact_name="test",
        contact_job_title="test",
        contact_email="test@email.com",
    )
    background_tasks = MagicMock()
    cipher = MagicMock()
    await sign_cla_organization(
        organization=organization_form,
        cla_service=cla_service,
        background_tasks=background_tasks,
        cipher=cipher,
        github_user=GitHubProfile(username="u", _id=1, emails=["u@email.com"]),
        launchpad_user=LaunchpadProfile(username="u", _id="lp1", emails=[]),
    )
    assert background_tasks.add_task.called
    assert cla_service.organization_cla_sign.called


class Organization(dict):
    def as_dict(self):
        return self


@pytest.mark.asyncio
@patch("app.cla.routes.templates.TemplateResponse")
async def test_visit_manage_organization(
    template_response,
):
    cipher = MagicMock()
    cipher.decrypt = MagicMock(return_value="1")
    template_response.return_value = MagicMock()
    organization_id = "encrypted_id"
    request = MagicMock()
    organization_repository = MagicMock()
    organization_repository.get_organization_by_id = AsyncMock(
        return_value=Organization({"id": 1})
    )

    await manage_organization(
        request=request,
        id=organization_id,
        organization_repository=organization_repository,
        cipher=cipher,
    )
    template_response.assert_called_with(
        request=request,
        name="manage_organization.j2",
        context={
            "organization": {"id": 1},
            "organization_id": "encrypted_id",
            "message": None,
            "email_sent": None,
        },
    )
    assert cipher.decrypt.called
    assert organization_repository.get_organization_by_id.called

    # Expect 404 if organization is not found
    cipher.decrypt.reset_mock()
    organization_repository.get_organization_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException):
        await manage_organization(
            request=request,
            id=organization_id,
            organization_repository=organization_repository,
            cipher=cipher,
        )
    assert cipher.decrypt.called
    assert organization_repository.get_organization_by_id.called
