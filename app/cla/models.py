from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator, ConfigDict
from pydantic_extra_types.country import CountryAlpha2

from app.cla.email_utils import (
    valid_email,
    valid_email_domain,
    clean_email_domain,
    clean_email,
)


class IndividualCreateForm(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "address": "123 Main St, Springfield, IL 62701",
                "country": "FR",
                "github_email": "john@example.com",
            }
        }
    )
    first_name: Annotated[str, StringConstraints(max_length=50)]
    last_name: Annotated[str, StringConstraints(max_length=50)]
    phone_number: Annotated[str, StringConstraints(max_length=20)]
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
        return self

    @model_validator(mode="after")
    def _emails_are_valid(self):
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
                "country": "United States",
            }
        }
    )
    name: Annotated[str, StringConstraints(max_length=100)]
    email_domain: Annotated[str, StringConstraints(max_length=100)]
    contact_name: Annotated[str, StringConstraints(max_length=100)]
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


class OrganizationCreationSuccess(BaseModel):
    message: str = (
        "Organization Contributor License Agreement (CLA) signed successfully"
    )
