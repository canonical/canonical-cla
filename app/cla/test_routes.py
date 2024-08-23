from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.datastructures import URL

from app.cla.routes import (
    check_cla,
    manage_organization,
    sign_cla_individual,
    sign_cla_organization,
)


@pytest.mark.asyncio
async def test_cla_check():
    cla_service = MagicMock()
    cla_service.check_cla = AsyncMock(return_value={"email1": True, "email2": False})
    response = await check_cla(emails=["email1", "email2"], cla_service=cla_service)

    assert response == {"email1": True, "email2": False}
    assert cla_service.check_cla.called


@pytest.mark.asyncio
async def test_sign_cla_individual():
    cla_service = MagicMock()
    cla_service.individual_cla_sign = AsyncMock()
    individual_form = {
        "first_name": "test",
        "last_name": "test",
        "address": "address",
        "country": "France",
        "phone_number": "1234567890",
        "github_email": "email1@email.com",
        "launchpad_email": "email2@email.com",
    }
    background_tasks = MagicMock()
    response = await sign_cla_individual(
        individual_form,
        cla_service=cla_service,
        gh_session="session",
        lp_session="session",
        background_tasks=background_tasks,
    )

    assert cla_service.individual_cla_sign.called
    assert background_tasks.add_task.called


@pytest.mark.asyncio
async def test_sign_cla_organization():
    cla_service = MagicMock()
    cla_service.organization_cla_sign = AsyncMock()
    organization_form = {
        "name": "test",
        "address": "address",
        "country": "France",
        "phone_number": "1234567890",
        "email_domain": "email.com",
    }
    background_tasks = MagicMock()
    request = MagicMock()
    cipher = MagicMock()
    response = await sign_cla_organization(
        request=request,
        organization=organization_form,
        cla_service=cla_service,
        background_tasks=background_tasks,
        cipher=cipher,
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

    response = await manage_organization(
        request=request,
        id=organization_id,
        organization_repository=organization_repository,
        cipher=cipher,
    )
    assert response.called_with(
        request=request,
        name="manage_organization.j2",
        context={"organization": {"id": 1}, "organization_id": "1", "message": None},
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
