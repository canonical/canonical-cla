"""
Poetry script: poetry run check.
Run ruff to check code quality and style.
"""

import argparse
from subprocess import run as process_run


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fix",
        help="Automatically fix linting issues",
        action=argparse.BooleanOptionalAction,
    )

    args = parser.parse_args()

    paths = ["app", "scripts", "migrations"]
    command = f"ruff check {' '.join(paths)}"

    if args.fix:
        command += " --fix"

    exit(process_run(command, shell=True).returncode)
