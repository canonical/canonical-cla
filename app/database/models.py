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
    github_account_id: Mapped[int | None] = mapped_column(Integer)
    github_email: Mapped[str | None] = mapped_column(String(100))
    launchpad_username: Mapped[str | None] = mapped_column(String(100))
    launchpad_account_id: Mapped[str | None] = mapped_column(String(100))
    launchpad_email: Mapped[str | None] = mapped_column(String(100))
    signed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow().replace(tzinfo=None)
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    def is_imported(self) -> bool:
        """Check if the individual has been imported."""
        most_recent_import = datetime.datetime(2024, 10, 1, 0, 0, 0)
        return self.signed_at < most_recent_import

    def __str__(self):
        github_info = (
            f"github: @{self.github_username} ({self.github_email})"
            if self.github_username
            else ""
        )
        launchpad_info = (
            f"launchpad: @{self.launchpad_username} ({self.launchpad_email})"
            if self.launchpad_username
            else ""
        )
        active = (
            f"active {(self.signed_at.isoformat())}"
            if self.revoked_at is None
            else "revoked"
        )
        return f"individual {self.id}: {self.first_name} {self.last_name} {github_info} {launchpad_info} status: {active}"


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

    def is_active(self) -> bool:
        """Check if the organization has an active CLA."""
        return self.revoked_at is None and self.signed_at is not None

    def __str__(self):
        active = (
            f"active {(self.signed_at.isoformat())}" if self.is_active() else "revoked"
        )
        return f"organization {self.id}: {self.name} domain: {self.email_domain} status: {active}"


AuditLogActionType = Literal[
    "SIGN",
    "REVOKE",
    "UPDATE",
    "DELETE",
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
    ip_address: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict[str, str] | None] = mapped_column(JSON)

    def __str__(self):
        details = (
            f"{self.details.get('name')} (domain: {self.details.get('email_domain')}, contact: {self.details.get('contact_name')}<{self.details.get('contact_email')}>)"
            if self.entity_type == "ORGANIZATION"
            else f"{self.details.get('first_name')} {self.details.get('last_name')} (github: {self.details.get('github_username')}<{self.details.get('github_email')}>, launchpad: {self.details.get('launchpad_username')}<{self.details.get('launchpad_email')}>)"
        )
        return f"{self.timestamp.isoformat()} audit log({self.id}): action({self.action}), IP({self.ip_address}), {self.entity_type}({self.entity_id}): {details}"
