from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.database.models import Role
from app.oidc.models import OIDCUserInfo
from app.oidc.service import oidc_user
from app.repository.user_role import UserRoleRepository, user_role_repository


class RequiresRole:
    """Requires a specific role to access the resource.

    Args:
        allowed_roles: List of roles that are allowed to access the resource.

    Example:
    ```
    @cla_router.get("/organization/delete", include_in_schema=False)
    async def delete_organization(
        authorized_user: OIDCUserInfo = Depends(requires_admin),
    ):  ...
    ```
    """

    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        user: Annotated[OIDCUserInfo, Depends(oidc_user)],
        repo: Annotated[UserRoleRepository, Depends(user_role_repository)],
    ) -> OIDCUserInfo:
        if not user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email required for role verification",
            )

        user_role = await repo.get_user_role(user.email.lower())

        if not user_role or user_role.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )

        return user


requires_admin = RequiresRole([Role.ADMIN])
requires_legal = RequiresRole([Role.ADMIN, Role.LEGAL_COUNSEL])
requires_community = RequiresRole([Role.ADMIN, Role.COMMUNITY_MANAGER])
