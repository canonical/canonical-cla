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

    lint_exit_code = process_run(command, shell=True).returncode
    if lint_exit_code != 0:
        print("Lint issues found. Please run 'poetry run format' to fix them.")
        return lint_exit_code
    type_check_status_code = process_run(
        "ty check --python-version=3.10", shell=True
    ).returncode
    if type_check_status_code != 0:
        print("Type check issues found. Please fix them manually.")
        return type_check_status_code
    print("No issues found ✅")
    return 0
