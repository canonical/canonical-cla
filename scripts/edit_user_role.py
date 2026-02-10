import argparse
import asyncio
import logging
from typing import Annotated

from fastapi import Depends

from app.database.models import Role
from app.repository.user_role import UserRoleRepository, user_role_repository
from scripts.common import run_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_user_role(
    email: str,
    role: Role,
    user_role_repository: Annotated[UserRoleRepository, Depends(user_role_repository)],
):
    user_role = await user_role_repository.create_user_role(email, role)
    print("User role created:")
    print(user_role)


async def remove_user_role(
    email: str,
    role: Role,
    user_role_repository: Annotated[UserRoleRepository, Depends(user_role_repository)],
):
    user_role = await user_role_repository.delete_user_role(email, role)
    print("User role removed:")
    print(user_role)


async def list_user_roles(
    user_role_repository: Annotated[UserRoleRepository, Depends(user_role_repository)],
):
    user_roles = await user_role_repository.get_all_user_roles()
    print("User roles:")
    for user_role in user_roles:
        print(user_role)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User Management Script")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_create = subparsers.add_parser("create", help="Create a new user")
    parser_create.add_argument("email", help="User email address")
    parser_create.add_argument("role", help="User role (e.g., admin, guest)")

    parser_remove = subparsers.add_parser("remove", help="Remove an existing user")
    parser_remove.add_argument("email", help="User email address")
    parser_remove.add_argument("role", help="User role")

    parser_list = subparsers.add_parser("list", help="List all users")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(run_command(create_user_role, email=args.email, role=args.role))
    elif args.command == "remove":
        asyncio.run(run_command(remove_user_role, email=args.email, role=args.role))
    elif args.command == "list":
        asyncio.run(run_command(list_user_roles))
    else:
        parser.print_help()
        exit(1)
