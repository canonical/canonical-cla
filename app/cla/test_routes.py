from unittest.mock import MagicMock, AsyncMock

import pytest

from app.cla.routes import check_cla, sign_cla_individual, sign_cla_organization


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
    response = await sign_cla_individual(
        individual_form,
        cla_service=cla_service,
        gh_session="session",
        lp_session="session",
    )

    assert cla_service.individual_cla_sign.called


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
    response = await sign_cla_organization(
        organization_form,
        cla_service=cla_service,
    )

    assert cla_service.organization_cla_sign.called
