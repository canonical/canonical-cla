from datetime import datetime
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import AuditLog, Organization
from app.middlewares import request_ip


class OrganizationRepository(Protocol):
    async def get_organizations(
        self,
        email_domains: list[str] | None = None,
    ) -> list[Organization]: ...

    async def create_organization(self, organization: Organization) -> Organization: ...

    async def get_organization_by_id(
        self, organization_id: int
    ) -> Organization | None: ...

    async def update_organization(self, organization: Organization) -> Organization: ...

    async def delete_organization(self, organization: Organization) -> Organization: ...


class SQLOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_organizations(
        self,
        email_domains: list[str] | None = None,
    ) -> list[Organization]:
        if not email_domains:
            return []
        query = select(Organization)
        query = query.where(Organization.email_domain.in_(email_domains))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_organization(self, organization: Organization) -> Organization:
        organization.signed_at = (
            organization.signed_at.replace(tzinfo=None)
            if organization.signed_at
            else None
        )
        self.session.add(organization)
        await self.session.flush()
        log = AuditLog(
            entity_type="ORGANIZATION",
            entity_id=organization.id,
            action="SIGN",
            details=organization.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def get_organization_by_id(self, organization_id: int) -> Organization | None:
        query = select(Organization).filter_by(id=organization_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_organization(self, organization: Organization) -> Organization:
        if not organization.id:
            raise ValueError("Organization ID is required for update")
        existing_organization = await self.get_organization_by_id(organization.id)
        if not existing_organization:
            raise ValueError(f"Organization with ID {organization.id} not found")
        organization.signed_at = existing_organization.signed_at
        organization.name = existing_organization.name
        organization.contact_name = existing_organization.contact_name
        organization.contact_email = existing_organization.contact_email
        organization.contact_job_title = existing_organization.contact_job_title

        organization.revoked_at = (
            organization.revoked_at.replace(tzinfo=None)
            if organization.revoked_at
            else None
        )

        self.session.add(organization)
        await self.session.flush()
        log = AuditLog(
            entity_type="ORGANIZATION",
            entity_id=organization.id,
            action="UPDATE",
            details=organization.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def delete_organization(self, organization: Organization) -> Organization:
        if not organization.id:
            raise ValueError("Organization ID is required for update")
        existing_organization = await self.get_organization_by_id(organization.id)
        if not existing_organization:
            raise ValueError(f"Organization with ID {organization.id} not found")
        organization.revoked_at = datetime.now()
        organization.signed_at = None

        self.session.add(organization)
        await self.session.flush()
        log = AuditLog(
            entity_type="ORGANIZATION",
            entity_id=organization.id,
            action="DELETE",
            details=organization.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization


def organization_repository(
    session: Annotated[AsyncSession, Depends(async_session)]
) -> OrganizationRepository:
    return SQLOrganizationRepository(session)
