from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import AuditLog, Individual


class IndividualRepository(Protocol):
    async def get_individuals(
        self,
        emails: list[str] | None = None,
        github_usernames: list[str] | None = None,
        launchpad_usernames: list[str] | None = None,
    ) -> list[Individual]: ...

    async def create_individual(self, individual: Individual) -> Individual: ...


class SQLIndividualRepository(IndividualRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_individuals(
        self,
        emails: list[str] | None = None,
        github_usernames: list[str] | None = None,
        launchpad_usernames: list[str] | None = None,
    ) -> list[Individual]:
        if not any([emails, github_usernames, launchpad_usernames]):
            return []

        query = select(Individual)
        if emails:
            query = query.where(
                or_(
                    Individual.github_email.in_(emails),
                    Individual.launchpad_email.in_(emails),
                )
            )
        if github_usernames:
            query = query.where(Individual.github_username.in_(github_usernames))
        if launchpad_usernames:
            query = query.where(Individual.launchpad_username.in_(launchpad_usernames))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_individual(self, individual: Individual) -> Individual:
        individual.signed_at = (
            individual.signed_at.replace(tzinfo=None) if individual.signed_at else None
        )
        self.session.add(individual)
        await self.session.flush()
        log = AuditLog(
            entity_type="INDIVIDUAL",
            entity_id=individual.id,
            action="SIGN",
            details=individual.as_dict(),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(individual)
        return individual


def individual_repository(
    session: Annotated[AsyncSession, Depends(async_session)]
) -> IndividualRepository:
    return SQLIndividualRepository(session)
