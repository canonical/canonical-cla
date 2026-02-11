from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic_extra_types.country import CountryAlpha2

from app.database.models import ProjectPlatform
from app.emails.email_utils import (
    clean_email,
    clean_email_domain,
    valid_email,
    valid_email_domain,
)


class IndividualCreateForm(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "address": "123 Main St, Springfield, IL 62701",
                "country": "FR",
                "github_email": "john@example.com",
            }
        }
    )
    first_name: Annotated[str, StringConstraints(max_length=50)]
    last_name: Annotated[str, StringConstraints(max_length=50)]
    address: Annotated[str, StringConstraints(max_length=400)]
    country: CountryAlpha2 = Field(
        ...,
        description="Country in the short name format.",
    )
    github_email: Annotated[str | None, StringConstraints(max_length=100)] = None
    launchpad_email: Annotated[str | None, StringConstraints(max_length=100)] = None

    @model_validator(mode="after")
    def _at_least_one_email(self):
        if not self.github_email and not self.launchpad_email:
            raise ValueError("At least one email must be provided")

        # check if the email addresses are valid
        if self.github_email:
            self.github_email = clean_email(self.github_email)
            if not valid_email(self.github_email):
                raise ValueError("Invalid GitHub email address")

        if self.launchpad_email:
            self.launchpad_email = clean_email(self.launchpad_email)
            if not valid_email(self.launchpad_email):
                raise ValueError("Invalid Launchpad email address")

        return self


class IndividualCreationSuccess(BaseModel):
    message: str = "Individual Contributor License Agreement (CLA) signed successfully"


class OrganizationCreateForm(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ACME Corp",
                "email_domain": "acme.com",
                "contact_name": "John Doe",
                "contact_email": "john@acme.com",
                "phone_number": "+1234567890",
                "address": "123 Main St, Springfield, IL 62701",
                "country": "FR",
            }
        }
    )
    name: Annotated[str, StringConstraints(max_length=100)]
    email_domain: Annotated[str, StringConstraints(max_length=100)]
    contact_name: Annotated[str, StringConstraints(max_length=100)]
    contact_job_title: Annotated[str, StringConstraints(max_length=100)]
    contact_email: Annotated[str, StringConstraints(max_length=100)]
    phone_number: Annotated[str | None, StringConstraints(max_length=20)] = None
    address: Annotated[str | None, StringConstraints(max_length=400)] = None
    country: CountryAlpha2 = Field(
        ...,
        description="Country in the short name format.",
    )

    @model_validator(mode="after")
    def _email_domain_is_valid(self):
        self.email_domain = clean_email_domain(self.email_domain)
        (is_valid, reason) = valid_email_domain(self.email_domain)
        if not is_valid:
            raise ValueError(reason)
        return self


class ExcludedProjectPayload(BaseModel):
    platform: Annotated[
        ProjectPlatform, Field(description="The platform of the project")
    ]
    full_name: Annotated[
        str,
        Field(
            description="The full name of the project, this includes the organization name and the project name.",
            examples=["canonical/ubuntu.com"],
        ),
    ]

    def __str__(self):
        return f"{self.platform.value}@{self.full_name}"


class ExcludedProjectListingPayload(BaseModel):
    projects: list[ExcludedProjectPayload]
    total: int


class ExcludedProjectCreatePayload(ExcludedProjectPayload):
    pass


class ExcludedProjectsResponse(BaseModel):
    project: ExcludedProjectPayload
    excluded: bool


class OrganizationCreationSuccess(BaseModel):
    message: str = (
        "Organization Contributor License Agreement (CLA) signed successfully"
    )


class CLACheckResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "emails": {
                    "dev1@ubuntu.com": True,
                    "dev2@example.com": False,
                },
                "github_usernames": {
                    "dev1": True,
                    "dev2": False,
                },
                "launchpad_usernames": {
                    "dev1": True,
                    "dev2": False,
                },
            }
        }
    )
    emails: dict[str, bool]
    github_usernames: dict[str, bool]
    launchpad_usernames: dict[str, bool]
