#!/usr/bin/env python3
"""
A CLI script to be run with Bash to import contributors from a JSON file.
Make sure environment variables are set before running this script.
"""

import argparse
import asyncio
import datetime
import json

from fastapi import Depends

from app.database.models import Individual
from app.repository.individual import IndividualRepository, individual_repository
from scripts.common import create_logger, run_command

logger = create_logger("import_contributors")


async def import_contributors(
    file_path: str,
    individual_repository: IndividualRepository = Depends(individual_repository),
):
    """
    Import contributors from a JSON file.
    """
    with open(file_path) as file:
        contributors = json.load(file)

    imported_count = 0
    logger.info("Importing contributors...")
    for contributor in contributors:
        contributor["signed_at"] = datetime.datetime.strptime(
            contributor["date"], "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=None)
        email_field_name = (
            "github_email" if contributor.get("github_username") else "launchpad_email"
        )
        contributor[email_field_name] = contributor["email"]
        contributor.pop("email")
        contributor.pop("date")
        try:
            individual = Individual(**contributor)
            await individual_repository.create_individual(individual)
            imported_count += 1
        except Exception as e:
            logger.error(
                f"Failed to import contributor {contributor[email_field_name]}: {e}"
            )
    logger.info(f"Imported {imported_count} contributors.")


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--input",
        help="JSON file with contributors",
        type=str,
        required=True,
    )
    args = arg_parser.parse_args()
    file_path = args.input

    asyncio.run(run_command(import_contributors, file_path=file_path))


if __name__ == "__main__":
    main()
