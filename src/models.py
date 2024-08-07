from datetime import datetime
from typing import Optional

from dateutil import parser
from pydantic import HttpUrl, PositiveInt, StringConstraints, field_validator
from pydantic_extra_types.country import CountryNumericCode
from sqlmodel import Field, Relationship, SQLModel
from typing_extensions import Annotated


class Individual(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    first_name: Annotated[str, StringConstraints(max_length=50)]
    last_name: Annotated[str, StringConstraints(max_length=50)]

    phone_number: Annotated[str, StringConstraints(max_length=20)]

    address: Annotated[str, StringConstraints(max_length=400)]
    country: CountryNumericCode

    github_username: Annotated[Optional[str], StringConstraints(max_length=100)] = (
        Field(unique=True)
    )
    github_account_id: PositiveInt
    github_email: Annotated[Optional[str], StringConstraints(max_length=100)] = Field(
        unique=True
    )

    launchpad_username: Annotated[Optional[str], StringConstraints(max_length=100)] = (
        Field(unique=True)
    )
    launchpad_account_id: Annotated[Optional[str], StringConstraints(max_length=100)]
    launchpad_email: Annotated[Optional[str], StringConstraints(max_length=100)] = (
        Field(unique=True)
    )

    signed_at: datetime

    revocation: Optional["Revocation"] = Relationship(back_populates="individual")

    # TZ causes issues with SQL select queries
    @field_validator("signed_at", mode="plain")
    def set_signed_at(cls, v):
        return parser.parse(v).replace(tzinfo=None)


class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: Annotated[str, StringConstraints(max_length=100)]
    email_hostname: Annotated[str, StringConstraints(max_length=100)]

    contact_name: Annotated[str, StringConstraints(max_length=100)]
    contact_email: Annotated[str, StringConstraints(max_length=100)]
    phone_number: Annotated[Optional[str], StringConstraints(max_length=20)]

    address: Annotated[Optional[str], StringConstraints(max_length=400)]
    country: CountryNumericCode

    salesforce_url: Annotated[str, HttpUrl]

    signed_at: datetime

    # TZ causes issues with SQL select queries
    @field_validator("signed_at", mode="plain")
    def set_signed_at(cls, v):
        return parser.parse(v).replace(tzinfo=None)


class Revocation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    individual_id: int = Field(foreign_key="individual.id")
    date_revoked: datetime

    individual: Individual = Relationship(back_populates="revocation")
