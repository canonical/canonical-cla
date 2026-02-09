import asyncio
import logging
import sys
from typing import Annotated

from fastapi import Depends

from app.database.models import Role
from app.repository.user_role import UserRoleRepository, user_role_repository
from scripts.common import run_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_first_admin(
    email: str,
    user_role_repository: Annotated[UserRoleRepository, Depends(user_role_repository)],
):
    user_role = await user_role_repository.create_user_role(email, Role.ADMIN)
    print("User role created:")
    print(user_role)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: poetry run python -m scripts.create_admin <email>")
        sys.exit(1)

    target_email = sys.argv[1]
    asyncio.run(run_command(create_first_admin, email=target_email))
