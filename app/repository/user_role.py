from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import AuditLog, Role, UserRole
from app.middlewares import request_ip


class UserRoleRepository(Protocol):
    async def get_user_role(self, email: str) -> UserRole | None: ...
    async def create_user_role(self, email: str, role: Role) -> UserRole: ...
    async def delete_user_role(self, email: str) -> UserRole: ...


class SQLUserRoleRepository(UserRoleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_role(self, email: str) -> UserRole | None:
        query = select(UserRole).where(UserRole.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user_role(self, email: str, role: Role) -> UserRole:
        # check if user role already exists
        user_role = await self.get_user_role(email)
        if user_role:
            raise ValueError(f"User role with email {email} already exists")
        new_user_role = UserRole(email=email, role=role)
        self.session.add(new_user_role)
        audit_log = AuditLog(
            entity_type="USER_ROLE",
            action="CREATE",
            details=new_user_role.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(audit_log)
        await self.session.commit()
        return new_user_role

    async def delete_user_role(self, email: str) -> UserRole:
        user_role = await self.get_user_role(email)
        if not user_role:
            raise ValueError(f"User role with email {email} not found")
        self.session.delete(user_role)
        await self.session.commit()
        audit_log = AuditLog(
            entity_type="USER_ROLE",
            action="DELETE",
            details=user_role.as_dict(),
            ip_address=request_ip(),
        )
        self.session.add(audit_log)
        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role


def user_role_repository(
    session: Annotated[AsyncSession, Depends(async_session)],
) -> UserRoleRepository:
    return SQLUserRoleRepository(session)
