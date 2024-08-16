from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import Organization, AuditLog


class OrganizationRepository(Protocol):
    async def get_organizations(
        self,
        email_domains: list[str] | None = None,
    ) -> list[Organization]: ...

    async def create_organization(self, organization: Organization) -> Organization: ...


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
        )
        self.session.add(log)
        await self.session.commit()
        return organization


def organization_repository(
    session: Annotated[AsyncSession, Depends(async_session)]
) -> OrganizationRepository:
    return SQLOrganizationRepository(session)
