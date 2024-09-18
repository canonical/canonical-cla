from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_asyncio import fixture

from app.cla.email_utils import clean_email
from app.cla.models import CLACheckResponse
from app.cla.service import CLAService
from app.database.models import Individual, Organization


@fixture
def cla_service():
    gh_service = MagicMock()
    lp_service = MagicMock()
    individual_repository = MagicMock()
    organization_repository = MagicMock()
    return CLAService(
        gh_service,
        lp_service,
        individual_repository,
        organization_repository,
    )


@fixture
def emails():
    return [
        "email1@example.com",
        "email2@example2.com",
        "email3@eXaMple3.coM ",
        "test",
        "email5@example.com",
    ]


@fixture
def usernames():
    return [
        "dev1",
        "dev2",
        "dev3",
    ]


@pytest.mark.asyncio
async def test_check_cla(cla_service, emails, usernames):
    cla_service.individuals_signed_cla = AsyncMock(return_value={"email1@example.com"})
    cla_service.organizations_signed_cla = AsyncMock(
        return_value={clean_email(emails[2])}
    )
    cla_service.check_cla_for_github_usernames = AsyncMock(
        return_value={"dev1": True, "dev2": False, "dev3": True}
    )
    cla_service.check_cla_for_launchpad_usernames = AsyncMock(
        return_value={"dev1": False, "dev2": True, "dev3": False}
    )

    response = await cla_service.check_cla(emails, usernames, usernames)
    assert response == CLACheckResponse(
        emails={
            emails[0]: True,
            emails[1]: False,
            emails[2]: True,
            emails[3]: False,
            emails[4]: False,
        },
        github_usernames={
            usernames[0]: True,
            usernames[1]: False,
            usernames[2]: True,
        },
        launchpad_usernames={
            usernames[0]: False,
            usernames[1]: True,
            usernames[2]: False,
        },
    )
    assert cla_service.individuals_signed_cla.called
    assert cla_service.organizations_signed_cla.called
    assert cla_service.check_cla_for_github_usernames.called
    assert cla_service.check_cla_for_launchpad_usernames.called


@pytest.mark.asyncio
async def test_individuals_signed_cla(cla_service, emails):
    cla_service.individual_repository.get_individuals = AsyncMock(
        return_value=[
            Individual(
                github_email="email1@example.com",
                launchpad_email="email2@example.com",
            ),
            Individual(
                github_email="email3@example3.com",
            ),
            Individual(launchpad_email="email5@example.com", revoked_at=datetime.now()),
        ]
    )
    response = await cla_service.individuals_signed_cla(
        [clean_email(email) for email in emails]
    )
    assert response == {
        "email1@example.com",
        "email2@example.com",
        "email3@example3.com",
    }

    # no db results
    cla_service.individual_repository.get_individuals = AsyncMock(return_value=[])
    response = await cla_service.individuals_signed_cla([])
    assert response == set()

    # no email provided
    response = await cla_service.individuals_signed_cla([])
    assert response == set()


@pytest.mark.asyncio
async def test_organizations_signed_cla(cla_service, emails):
    cla_service.organization_repository.get_organizations = AsyncMock(
        return_value=[
            # signed
            Organization(email_domain="example.com", signed_at=datetime.now()),
            # not signed
            Organization(email_domain="example2.com"),
            # revoked
            Organization(
                email_domain="example3.com",
                revoked_at=datetime.now(),
                signed_at=datetime.now(),
            ),
        ]
    )
    cleaned_emails = [clean_email(email) for email in emails]
    response = await cla_service.organizations_signed_cla(cleaned_emails)
    assert response == {
        # only emails with domain example.com are signed
        cleaned_emails[0],
        cleaned_emails[4],
    }

    # no db results
    cla_service.organization_repository.get_organizations = AsyncMock(return_value=[])
    response = await cla_service.organizations_signed_cla(cleaned_emails)

    assert response == set()

    # no email provided
    response = await cla_service.organizations_signed_cla([])
    assert response == set()
