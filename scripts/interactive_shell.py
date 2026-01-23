#!/usr/bin/env python3
"""
Interactive shell for debugging production environment.

Usage:
    python scripts/interactive_shell.py
"""

import asyncio
import os
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import httpx
import nest_asyncio
from fastapi import Depends
from IPython.terminal.embed import InteractiveShellEmbed
from sqlalchemy.ext.asyncio import AsyncSession

import app.database.models as models
from app.cla.service import CLAService, cla_service
from app.database.connection import async_session
from app.github.service import GithubService, github_service
from app.github.webhook_service import GithubWebhookService, github_webhook_service
from app.http_client import http_client
from app.launchpad.service import LaunchpadService, launchpad_service
from app.middlewares import request_ip_address_context_var
from app.oidc.service import OIDCService, oidc_service
from app.repository.individual import IndividualRepository, individual_repository
from app.repository.organization import OrganizationRepository, organization_repository
from scripts.common import Colors, create_logger, run_command

nest_asyncio.apply()

logger = create_logger("interactive_shell")


def create_namespace(
    http_client: httpx.AsyncClient = Depends(http_client),
    individual_repository: IndividualRepository = Depends(individual_repository),
    organization_repository: OrganizationRepository = Depends(organization_repository),
    github_service: GithubService = Depends(github_service),
    launchpad_service: LaunchpadService = Depends(launchpad_service),
    oidc_service: OIDCService = Depends(oidc_service),
    cla_service: CLAService = Depends(cla_service),
    github_webhook_service: GithubWebhookService = Depends(github_webhook_service),
    session: AsyncSession = Depends(async_session),
) -> dict[str, dict[str, Any]]:
    """
    This function now acts as a Dependency Provider.
    It resolves all services and bundles them into the dictionary.
    """

    namespace = {
        "services": {
            "github_service": github_service,
            "launchpad_service": launchpad_service,
            "oidc_service": oidc_service,
            "cla_service": cla_service,
            "github_webhook_service": github_webhook_service,
        },
        "repositories": {
            "individual_repository": individual_repository,
            "organization_repository": organization_repository,
        },
        "utils": {
            "database_session": session,
            "http_client": http_client,
        },
        "common": {
            "sys": sys,
        },
        "models": {},
    }

    # Database models
    for name, model in models.__dict__.items():
        if (
            isinstance(model, type)
            and issubclass(model, models.Base)
            and model is not models.Base
        ):
            namespace["models"][name] = model

    namespace.update({"__name__": "__main__"})
    return namespace


def print_namespace_info(namespace: dict[str, dict[str, Any]]):
    """Print information about available objects in the namespace dynamically."""

    def print_separator():
        """Print a separator line matching the terminal width."""
        try:
            width = os.get_terminal_size().columns
        except (OSError, AttributeError):
            width = 70
        print(f"{Colors.BOLD}{Colors.CYAN}{'_' * width}{Colors.RESET}")

    print_separator()
    print(f"{Colors.BOLD}{Colors.CYAN}Interactive Debug Shell{Colors.RESET}")
    print_separator()
    print(f"\n{Colors.BOLD}Available objects:{Colors.RESET}")

    for category_name, items in namespace.items():
        # Skip internal keys or non-dict items (like __name__)
        if not isinstance(items, dict) or not items:
            continue

        print(f"  {Colors.BOLD}{Colors.MAGENTA}{category_name}:{Colors.RESET}")

        for key, value in sorted(items.items()):
            # Get a description of the value
            if isinstance(value, type):
                desc = f"{value.__name__} model class"
            else:
                value_type = type(value).__name__
                desc = f"{value_type} instance"

            print(
                f"    {Colors.GRAY}-{Colors.RESET} {Colors.BLUE}{category_name}.{key}{Colors.RESET}: {Colors.GRAY}{desc}{Colors.RESET}"
            )

    print(f"\n{Colors.BOLD}Async operations:{Colors.RESET}")
    print(
        f"{Colors.BOLD}You can use {Colors.YELLOW}'await'{Colors.RESET} directly in this shell"
    )

    examples = [
        "result = await utils.http_client.get('https://api.github.com')",
        "result = await services.cla_service.check_cla(emails=['test@example.com'])",
        "users = await repositories.individual_repository.get_individuals(emails=['...'])",
        "new_user = models.Individual(email='test@test.com')",
    ]
    for example in examples:
        print(f"  {Colors.GRAY}-{Colors.RESET} {Colors.GREEN}{example}{Colors.RESET}")
    print_separator()
    print(f"\n{Colors.BOLD}{Colors.GREEN}Starting interactive shell...{Colors.RESET}\n")


async def interactive_shell(
    namespace_dict: dict[str, dict[str, Any]] = Depends(create_namespace),
):
    """
    Launch interactive shell.
    All dependencies are already resolved and injected via 'namespace_dict'.
    """
    # Set a default IP address for request_ip context variable
    request_ip_address_context_var.set("127.0.0.1")

    print_namespace_info(namespace_dict)

    # Convert to SimpleNamespace for dot-notation usage (e.g., services.github_service)
    shell_namespace = {}
    for key, value in namespace_dict.items():
        if isinstance(value, dict) and key != "__name__":
            shell_namespace[key] = SimpleNamespace(**value)
        else:
            shell_namespace[key] = value

    shell = InteractiveShellEmbed(user_ns=shell_namespace, colors="neutral")
    shell.autoawait = True
    shell()


def setup_environment():
    """Set up the environment for the interactive shell."""

    pythonpath = os.environ.get("PYTHONPATH", "")
    additional_path = "/usr/lib/python3.10/site-packages"
    if pythonpath:
        os.environ["PYTHONPATH"] = f"{pythonpath}:{additional_path}"
    else:
        os.environ["PYTHONPATH"] = additional_path
    # In production, find the existing uvicorn process and use its environment variables
    try:
        user_id = os.getuid()
        result = subprocess.run(
            ["pgrep", "-u", str(user_id), "-f", "uvicorn"],
            capture_output=True,
            text=True,
            check=True,
        )

        pids = result.stdout.strip().split("\n")
        if not pids or not pids[0]:
            logger.warning("No uvicorn process found for current user")
            return

        pid = pids[0]
        logger.info(f"Found uvicorn process with PID: {pid}")

        # Read environment variables from /proc/<pid>/environ
        environ_path = f"/proc/{pid}/environ"
        if not os.path.exists(environ_path):
            logger.warning(f"Environment file not found: {environ_path}")
            return

        with open(environ_path, "rb") as f:
            environ_data = f.read()

        # Parse null-delimited environment variables
        # Split by null byte and filter out empty strings
        env_vars = [var.decode("utf-8") for var in environ_data.split(b"\x00") if var]

        # Set environment variables
        for env_var in env_vars:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                os.environ[key] = value

        logger.info(
            f"Loaded {len(env_vars)} environment variables from uvicorn process"
        )

        logger.info("Environment setup complete")

    except subprocess.CalledProcessError:
        logger.warning("Could not find uvicorn process using pgrep")
    except FileNotFoundError:
        logger.warning("pgrep command not found. Make sure you're on a Linux system.")
    except Exception as e:
        logger.error(f"Error setting up environment: {e}", exc_info=True)


def main():
    """Main entry point."""
    setup_environment()
    asyncio.run(run_command(interactive_shell))


if __name__ == "__main__":
    main()
