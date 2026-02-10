from datetime import datetime
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import AuditLog, ExcludedProject, ProjectPlatform
from app.middlewares import request_ip


class ExcludedProjectRepository(Protocol):
    async def filter_excluded_projects(
        self,
        limit: int,
        offset: int,
        descending: bool | None,
        query: str | None,
        platform: ProjectPlatform | None,
    ) -> tuple[list[ExcludedProject], int]: ...
    async def get_projects_excluded(
        self, projects: list[ExcludedProject]
    ) -> list[tuple[ExcludedProject, bool]]: ...
    async def add_excluded_project(
        self, project: ExcludedProject
    ) -> ExcludedProject: ...
    async def delete_excluded_project(
        self, project: ExcludedProject
    ) -> ExcludedProject: ...


class SQLExcludedProjectRepository(ExcludedProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def filter_excluded_projects(
        self,
        limit: int,
        offset: int,
        descending: bool | None = True,
        query: str | None = None,
        platform: ProjectPlatform | None = None,
    ) -> tuple[list[ExcludedProject], int]:
        stmt = select(ExcludedProject)
        if platform:
            stmt = stmt.where(ExcludedProject.platform == platform)
        if query:
            stmt = stmt.where(ExcludedProject.full_name.ilike(f"%{query.strip()}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if descending:
            stmt = stmt.order_by(ExcludedProject.created_at.desc())
        else:
            stmt = stmt.order_by(ExcludedProject.created_at.asc())

        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)

        return list(result.scalars().all()), total

    async def add_excluded_project(self, project: ExcludedProject) -> ExcludedProject:
        """
        Adds a new excluded project to the database.
        """
        project.created_at = datetime.now().replace(tzinfo=None)
        self.session.add(project)
        audit_log = AuditLog(
            entity_type="EXCLUDED_PROJECT",
            action="ADD",
            details=project.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(audit_log)
        await self.session.commit()
        return project

    async def delete_excluded_project(
        self, project: ExcludedProject
    ) -> ExcludedProject:
        """
        Removes an excluded project from the database.
        """
        result = await self.session.execute(
            select(ExcludedProject).where(
                ExcludedProject.platform == project.platform,
                ExcludedProject.full_name == project.full_name,
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Excluded project {project.full_name} not found",
            )
        await self.session.delete(existing)
        audit_log = AuditLog(
            entity_type="EXCLUDED_PROJECT",
            action="DELETE",
            details=existing.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(audit_log)
        await self.session.commit()
        return existing

    async def get_projects_excluded(
        self, projects: list[ExcludedProject]
    ) -> list[tuple[ExcludedProject, bool]]:
        """
        Checks if the given projects are excluded (exist) in the database.
        """
        if not projects:
            return []

        # Build a single query to find any matching records in the DB
        # We look for rows where (platform == P AND full_name == N)
        conditions = [
            and_(
                ExcludedProject.platform == project.platform,
                ExcludedProject.full_name == project.full_name,
            )
            for project in projects
        ]

        query = select(ExcludedProject.platform, ExcludedProject.full_name).where(
            or_(*conditions)
        )

        db_result = await self.session.execute(query)

        # Create a set of found keys (platform, full_name) for O(1) lookup
        # resulting rows will be tuples like ('github', 'canonical/repo')
        found_keys = set(db_result.all())

        # Map the original projects to the boolean result
        return [
            (project, (project.platform, project.full_name) in found_keys)
            for project in projects
        ]


def excluded_project_repository(
    session: Annotated[AsyncSession, Depends(async_session)],
) -> ExcludedProjectRepository:
    return SQLExcludedProjectRepository(session)
