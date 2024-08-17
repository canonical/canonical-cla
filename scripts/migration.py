"""
Poetry script: poetry run format.
Run a bash command to generate or apply database migrations.
"""

import argparse
import subprocess


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate",
        help="Generate a migration",
        type=str,
        metavar='"Migration file description"',
    )
    parser.add_argument(
        "--apply",
        help="Apply migrations",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--reset",
        help="Reset the database",
        action=argparse.BooleanOptionalAction,
    )
    args = parser.parse_args()
    # run alembic
    command: str
    if args.generate:
        command = f"alembic revision --autogenerate -m '{args.generate}'"
    elif args.apply:
        command = "alembic upgrade head"
    elif args.reset:
        command = "alembic downgrade base"
    else:
        parser.print_help()
        exit(1)
    exit(subprocess.run(command, shell=True).returncode)
