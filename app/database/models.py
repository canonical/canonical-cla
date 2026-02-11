import datetime
import enum

from sqlalchemy import JSON, DateTime, Enum, Integer, String, func
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
    address: Mapped[str] = mapped_column(String(400))
    country: Mapped[str] = mapped_column(String(50))
    github_username: Mapped[str | None] = mapped_column(String(100))
    github_account_id: Mapped[int | None] = mapped_column(Integer)
    github_email: Mapped[str | None] = mapped_column(String(100))
    launchpad_username: Mapped[str | None] = mapped_column(String(100))
    launchpad_account_id: Mapped[str | None] = mapped_column(String(100))
    launchpad_email: Mapped[str | None] = mapped_column(String(100))
    signed_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
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
    contact_job_title: Mapped[str] = mapped_column(String(100))
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
            f"active {(self.signed_at.isoformat())}"
            if self.signed_at and self.is_active()
            else "revoked"
        )
        return f"organization {self.id}: {self.name} domain: {self.email_domain} status: {active}"


class Role(str, enum.Enum):
    """Role of an OIDC user."""

    ADMIN = "admin"
    COMMUNITY_MANAGER = "community_manager"
    LEGAL_COUNSEL = "legal_counsel"


class UserRole(Base):
    __tablename__ = "user_role"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    def __str__(self):
        return f"User {self.email} has role {self.role}"


class ProjectPlatform(str, enum.Enum):
    GITHUB = "github"
    LAUNCHPAD = "launchpad"


class ExcludedProject(Base):
    __tablename__ = "excluded_project"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[ProjectPlatform] = mapped_column(
        Enum(
            ProjectPlatform,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
    )

    def __str__(self):
        return f"{self.platform}@{self.full_name}"


class AuditEntityType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    ORGANIZATION = "ORGANIZATION"
    USER_ROLE = "USER_ROLE"
    EXCLUDED_PROJECT = "EXCLUDED_PROJECT"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[AuditEntityType] = mapped_column(
        Enum(
            AuditEntityType,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    ip_address: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict[str, str] | None] = mapped_column(JSON)

    def __str__(self):
        formatted_details = "N/A"
        if self.details:
            if self.entity_type == AuditEntityType.INDIVIDUAL:
                individual = Individual(**self.details)
                formatted_details = f"{individual.first_name} {individual.last_name} (github: {individual.github_username}<{individual.github_email}>, launchpad: {individual.launchpad_username}<{individual.launchpad_email}>)"
            elif self.entity_type == AuditEntityType.ORGANIZATION:
                organization = Organization(**self.details)
                formatted_details = f"{organization.name} (domain: {organization.email_domain}, contact: {organization.contact_name}<{organization.contact_email}>)"
            elif self.entity_type == AuditEntityType.USER_ROLE:
                user_role = UserRole(**self.details)
                formatted_details = f"{user_role.email} has role {user_role.role}"
            elif self.entity_type == AuditEntityType.EXCLUDED_PROJECT:
                excluded_project = ExcludedProject(**self.details)
                formatted_details = f"{excluded_project.full_name} (platform: {excluded_project.platform})"
        return f"{self.timestamp.isoformat()} audit log({self.id}): action({self.action}), IP({self.ip_address}), {self.entity_type}: {formatted_details}"
