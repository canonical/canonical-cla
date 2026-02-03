import logging

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError

import app.emails.blocked.error_messages as email_error_messages
from app.cla.models import (
    CLACheckResponse,
    IndividualCreateForm,
    OrganizationCreateForm,
)
from app.database.models import Individual, Organization
from app.emails.blocked.blocked_emails import is_email_blocked
from app.emails.blocked.excluded_emails import excluded_email
from app.emails.email_utils import clean_email, email_domain
from app.github.models import GitHubProfile
from app.github.service import GithubService, github_service
from app.launchpad.models import LaunchpadProfile
from app.launchpad.service import LaunchpadService, launchpad_service
from app.repository.individual import IndividualRepository, individual_repository
from app.repository.organization import OrganizationRepository, organization_repository

logger = logging.getLogger(__name__)


class CLAService:
    def __init__(
        self,
        github_service: GithubService,
        launchpad_service: LaunchpadService,
        individual_repository: IndividualRepository,
        organization_repository: OrganizationRepository,
    ):
        self.github_service = github_service
        self.launchpad_service = launchpad_service
        self.individual_repository = individual_repository
        self.organization_repository = organization_repository

    async def check_cla(
        self,
        emails: list[str],
        github_usernames: list[str],
        launchpad_usernames: list[str],
    ) -> CLACheckResponse:
        return CLACheckResponse(
            emails=await self.check_cla_for_emails(emails) if emails else {},
            github_usernames=(
                await self.check_cla_for_github_usernames(github_usernames)
                if github_usernames
                else {}
            ),
            launchpad_usernames=(
                await self.check_cla_for_launchpad_usernames(launchpad_usernames)
                if launchpad_usernames
                else {}
            ),
        )

    async def check_cla_for_github_usernames(
        self, usernames: list[str]
    ) -> dict[str, bool]:
        Individuals_signed = (
            await self.individual_repository.get_individuals_by_github_usernames(
                usernames
            )
        )
        signed_usernames = {
            individual.github_username
            for individual in Individuals_signed
            if individual.github_username
        }
        return {username: username in signed_usernames for username in usernames}

    async def check_cla_for_launchpad_usernames(
        self, usernames: list[str]
    ) -> dict[str, bool]:
        Individuals_signed = (
            await self.individual_repository.get_individuals_by_launchpad_usernames(
                usernames
            )
        )
        signed_usernames = {
            individual.launchpad_username
            for individual in Individuals_signed
            if individual.launchpad_username
        }
        return {username: username in signed_usernames for username in usernames}

    async def check_cla_for_emails(self, emails: list[str]) -> dict[str, bool]:
        # map given user emails to normalized emails
        # and respond with user's emails once checked
        normalized_emails = {raw_email: clean_email(raw_email) for raw_email in emails}
        emails_set = set(normalized_emails.values())
        signed_individuals = await self.individuals_signed_cla(list(emails_set))
        signed_organizations = await self.organizations_signed_cla(
            # remove who signed from the organization check
            list(emails_set - signed_individuals)
        )
        signed_emails = signed_individuals.union(signed_organizations)
        # fill not signed emails with False
        return {
            raw_email: normalized_email in signed_emails
            for raw_email, normalized_email in normalized_emails.items()
        }

    async def individuals_signed_cla(self, emails: list[str]) -> set[str]:
        individuals = await self.individual_repository.get_individuals(emails=emails)
        signed_emails = set()
        for individual in individuals:
            if individual.github_email and not individual.revoked_at:
                signed_emails.add(individual.github_email)
            if individual.launchpad_email and not individual.revoked_at:
                signed_emails.add(individual.launchpad_email)
        return signed_emails

    async def organizations_signed_cla(self, emails: list[str]) -> set[str]:
        # map of email domain to emails
        email_domains = {}
        for email in emails:
            email_domain = email.split("@")[-1]
            email_domains[email_domain] = email_domains.get(email_domain, set())
            email_domains[email_domain].add(email)

        organizations = await self.organization_repository.get_organizations(
            email_domains=list(email_domains.keys())
        )
        signed_emails = set()
        for organization in organizations:
            if not organization.revoked_at and organization.signed_at:
                signed_emails.update(email_domains[organization.email_domain])

        return signed_emails

    async def individual_cla_sign(
        self,
        individual_form: IndividualCreateForm,
        github_user: GitHubProfile | None,
        launchpad_user: LaunchpadProfile | None,
    ) -> Individual:
        # Validate the provided emails and ensure they belong to the authenticated user
        if github_user is None and launchpad_user is None:
            raise HTTPException(
                status_code=400,
                detail="At least one email address is required to sign the CLA",
            )

        if individual_form.github_email and github_user is None:
            raise HTTPException(
                status_code=400,
                detail="The selected GitHub email does not match any of the authenticated user emails",
            )
        if individual_form.launchpad_email and launchpad_user is None:
            raise HTTPException(
                status_code=400,
                detail="The selected Launchpad email does not match any of the authenticated user emails",
            )

        for email in [individual_form.github_email, individual_form.launchpad_email]:
            if not email:
                continue
            if excluded_email(email):
                raise HTTPException(
                    status_code=400,
                    detail=email_error_messages.EXCLUDED_EMAIL_ERROR_MESSAGE,
                )
            if is_email_blocked(email):
                raise HTTPException(
                    status_code=400,
                    detail=email_error_messages.BLOCKED_EMAIL_ERROR_MESSAGE,
                )

        if (
            github_user
            and individual_form.github_email
            and individual_form.github_email.lower()
            not in [email.lower() for email in github_user.emails]
        ):
            raise HTTPException(
                status_code=400,
                detail="The selected GitHub email does not match any of the authenticated user emails",
            )

        if (
            launchpad_user
            and individual_form.launchpad_email
            and individual_form.launchpad_email.lower()
            not in [email.lower() for email in launchpad_user.emails]
        ):
            raise HTTPException(
                status_code=400,
                detail="The selected Launchpad email does not match any of the authenticated user emails",
            )

        # check if the email addresses are unique
        emails = []
        if individual_form.github_email:
            emails.append(individual_form.github_email)
        if individual_form.launchpad_email:
            emails.append(individual_form.launchpad_email)
        existing_individuals = await self.individual_repository.get_individuals(
            emails=emails
        )

        for existing_individual in existing_individuals:
            # allow duplicated emails if the individual is imported
            if not existing_individual.is_imported():
                raise HTTPException(
                    status_code=400,
                    detail="The provided email address is already associated with a CLA",
                )

        # Create the individual record in the database
        individual = Individual(
            **individual_form.model_dump(),
            github_username=github_user.username if github_user else None,
            github_account_id=github_user._id if github_user else None,
            launchpad_username=(launchpad_user.username if launchpad_user else None),
            launchpad_account_id=launchpad_user._id if launchpad_user else None,
        )
        try:
            return await self.individual_repository.create_individual(individual)
        except IntegrityError as e:
            logger.info("Failed to create individual", exc_info=e)
            provided_email: str
            if not individual.github_email:
                provided_email = "Launchpad email"
            elif not individual.launchpad_account_id:
                provided_email = "GitHub email"
            else:
                provided_email = "GitHub or Launchpad email"
            raise HTTPException(
                status_code=409,
                detail=f"An individual with the provided {provided_email} already signed the CLA",
            ) from e

    async def organization_cla_sign(
        self,
        organization_form: OrganizationCreateForm,
        github_user: GitHubProfile | None,
        launchpad_user: LaunchpadProfile | None,
    ) -> Organization:
        owned_email_domains = set()
        emails = set[str]()
        if github_user:
            emails.update(github_user.emails)
        if launchpad_user:
            emails.update(launchpad_user.emails)
        for email in emails:
            owned_email_domains.add(email_domain(email))

        if organization_form.email_domain not in owned_email_domains:
            raise HTTPException(
                status_code=400,
                detail="The provided email domain does not match any of the authenticated user emails",
            )
        if is_email_blocked(organization_form.email_domain):
            raise HTTPException(
                status_code=400,
                detail=email_error_messages.BLOCKED_EMAIL_DOMAIN_ERROR_MESSAGE,
            )

        organization = Organization(**organization_form.model_dump())
        try:
            return await self.organization_repository.create_organization(organization)
        except IntegrityError as e:
            raise HTTPException(
                status_code=409,
                detail="An organization with the provided email domain already signed the CLA",
            ) from e


async def cla_service(
    github_service: GithubService = Depends(github_service),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
    individual_repository: IndividualRepository = Depends(individual_repository),
    organization_repository: OrganizationRepository = Depends(organization_repository),
) -> CLAService:
    return CLAService(
        github_service,
        launchpad_service,
        individual_repository,
        organization_repository,
    )
