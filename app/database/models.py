import datetime
from typing import Literal

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, class_mapper, mapped_column


# Base class
class Base(DeclarativeBase):

    def as_dict(self):
        obj_dict = {
            column.key: getattr(self, column.key)
            for column in class_mapper(self.__class__).columns
        }
        # Serialize datetime objects
        for key, value in obj_dict.items():
            if isinstance(value, datetime.datetime):
                obj_dict[key] = value.isoformat()
        return obj_dict


# Models
class Individual(Base):
    __tablename__ = "individual"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    phone_number: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(400))
    country: Mapped[str] = mapped_column(String(50))
    github_username: Mapped[str | None] = mapped_column(String(100))
    github_account_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    github_email: Mapped[str | None] = mapped_column(String(100), unique=True)
    launchpad_username: Mapped[str | None] = mapped_column(String(100))
    launchpad_account_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    launchpad_email: Mapped[str | None] = mapped_column(String(100), unique=True)
    signed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow().replace(tzinfo=None)
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email_domain: Mapped[str] = mapped_column(String(100), unique=True)
    contact_name: Mapped[str] = mapped_column(String(100))
    contact_email: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(400))
    country: Mapped[str] = mapped_column(String(50))
    salesforce_url: Mapped[str | None] = mapped_column(String(255))
    signed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)


AuditLogActionType = Literal[
    "SIGN",
    "REVOKE",
    "UPDATE",
]

AuditEntityType = Literal[
    "INDIVIDUAL",
    "ORGANIZATION",
]


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[AuditLogActionType]
    entity_type: Mapped[AuditEntityType]
    entity_id: Mapped[int]
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow().replace(tzinfo=None)
    )

    details: Mapped[dict[str, str] | None] = mapped_column(JSON)
