from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pytest_asyncio import fixture

from app.cla.email_utils import clean_email
from app.cla.models import CLACheckResponse, IndividualCreateForm
from app.cla.service import CLAService
from app.database.models import Individual, Organization
from app.github.models import GitHubProfile
from app.launchpad.models import LaunchpadProfile


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


@pytest.mark.asyncio
async def test_individual_cla_sign_case_insensitive_github_email(cla_service):
    """Test that GitHub email validation is case-insensitive"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email="User@Example.Com",  # Mixed case
        launchpad_email=None,
    )

    # Mock GitHub profile with lowercase email
    github_profile = GitHubProfile(
        username="testuser",
        _id="123456",
        emails=["user@example.com"],  # Lowercase in profile
    )

    # Setup mocks
    cla_service.github_service.profile = AsyncMock(return_value=github_profile)
    cla_service.individual_repository.get_individuals = AsyncMock(return_value=[])
    cla_service.individual_repository.create_individual = AsyncMock(
        return_value=Individual(**individual_form.model_dump())
    )

    # Should not raise an exception due to case mismatch
    result = await cla_service.individual_cla_sign(individual_form, "gh_session", None)

    assert result is not None
    cla_service.individual_repository.create_individual.assert_called_once()


@pytest.mark.asyncio
async def test_individual_cla_sign_case_insensitive_launchpad_email(cla_service):
    """Test that Launchpad email validation is case-insensitive"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email=None,
        launchpad_email="User@Example.Com",  # Mixed case
    )

    # Mock Launchpad profile with lowercase email
    launchpad_profile = LaunchpadProfile(
        username="testuser",
        _id="123456",
        emails=["user@example.com"],  # Lowercase in profile
    )

    # Setup mocks
    cla_service.launchpad_service.profile = AsyncMock(return_value=launchpad_profile)
    cla_service.individual_repository.get_individuals = AsyncMock(return_value=[])
    cla_service.individual_repository.create_individual = AsyncMock(
        return_value=Individual(**individual_form.model_dump())
    )

    # Should not raise an exception due to case mismatch
    result = await cla_service.individual_cla_sign(
        individual_form, None, {"session": "data"}
    )

    assert result is not None
    cla_service.individual_repository.create_individual.assert_called_once()


@pytest.mark.asyncio
async def test_individual_cla_sign_multiple_profile_emails_case_insensitive(
    cla_service,
):
    """Test case-insensitive matching when profile has multiple emails"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email="PRIMARY@Example.Com",  # Mixed case, should match second email
        launchpad_email=None,
    )

    # Mock GitHub profile with multiple emails in different cases
    github_profile = GitHubProfile(
        username="testuser",
        _id="123456",
        emails=["secondary@test.com", "primary@example.com", "tertiary@test.org"],
    )

    # Setup mocks
    cla_service.github_service.profile = AsyncMock(return_value=github_profile)
    cla_service.individual_repository.get_individuals = AsyncMock(return_value=[])
    cla_service.individual_repository.create_individual = AsyncMock(
        return_value=Individual(**individual_form.model_dump())
    )

    # Should match the second email in the profile despite case differences
    result = await cla_service.individual_cla_sign(individual_form, "gh_session", None)

    assert result is not None
    cla_service.individual_repository.create_individual.assert_called_once()


@pytest.mark.asyncio
async def test_individual_cla_sign_github_email_mismatch_error_message(cla_service):
    """Test that GitHub email mismatch returns the correct error message"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email="user@different.com",
        launchpad_email=None,
    )

    # Mock GitHub profile with different emails
    github_profile = GitHubProfile(
        username="testuser",
        _id="123456",
        emails=["user@example.com", "test@example.com"],
    )

    cla_service.github_service.profile = AsyncMock(return_value=github_profile)

    with pytest.raises(HTTPException) as exc_info:
        await cla_service.individual_cla_sign(individual_form, "gh_session", None)

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "The selected GitHub email does not match any of the authenticated user emails"
    )


@pytest.mark.asyncio
async def test_individual_cla_sign_launchpad_email_mismatch_error_message(cla_service):
    """Test that Launchpad email mismatch returns the correct error message"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email=None,
        launchpad_email="user@different.com",
    )

    # Mock Launchpad profile with different emails
    launchpad_profile = LaunchpadProfile(
        username="testuser",
        _id="123456",
        emails=["user@example.com", "test@example.com"],
    )

    cla_service.launchpad_service.profile = AsyncMock(return_value=launchpad_profile)

    with pytest.raises(HTTPException) as exc_info:
        await cla_service.individual_cla_sign(
            individual_form, None, {"session": "data"}
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "The selected Launchpad email does not match any of the authenticated user emails"
    )


@pytest.mark.asyncio
async def test_individual_cla_sign_both_emails_case_insensitive(cla_service):
    """Test case-insensitive validation with both GitHub and Launchpad emails"""
    individual_form = IndividualCreateForm(
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
        address="123 Test St",
        country="US",
        github_email="GitHub@Example.Com",
        launchpad_email="LaunchPad@Example.Com",
    )

    # Mock profiles with lowercase emails
    github_profile = GitHubProfile(
        username="testuser", _id="123456", emails=["github@example.com"]
    )
    launchpad_profile = LaunchpadProfile(
        username="testuser", _id="654321", emails=["launchpad@example.com"]
    )

    # Setup mocks
    cla_service.github_service.profile = AsyncMock(return_value=github_profile)
    cla_service.launchpad_service.profile = AsyncMock(return_value=launchpad_profile)
    cla_service.individual_repository.get_individuals = AsyncMock(return_value=[])
    cla_service.individual_repository.create_individual = AsyncMock(
        return_value=Individual(**individual_form.model_dump())
    )

    # Should not raise an exception
    result = await cla_service.individual_cla_sign(
        individual_form, "gh_session", {"session": "data"}
    )

    assert result is not None
    cla_service.individual_repository.create_individual.assert_called_once()
