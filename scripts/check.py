"""
Poetry script: poetry run check.
Run a bash command to check the project using ruff and djlint.
"""

import argparse
from subprocess import run as process_run

from scripts.common import Colors

template_paths = [
    "app/cla/templates/*",
    "app/notifications/templates/*",
]

python_paths = ["app", "scripts", "migrations"]


def check_python(args: argparse.Namespace):
    command = f"ruff check {' '.join(python_paths)}"
    if args.fix:
        command += " --fix --unsafe-fixes"
    lint_exit_code = process_run(command, shell=True).returncode
    if lint_exit_code != 0:
        print(
            f"{Colors.YELLOW}Ruff issues found. Please run 'poetry run check --fix' to fix them, or manually fix them.{Colors.RESET}"
        )
        return lint_exit_code

    type_check_exit_code = process_run(
        "ty check --python-version=3.10", shell=True
    ).returncode
    if type_check_exit_code != 0:
        print(
            f"{Colors.YELLOW}Type check issues found. Please fix them manually.{Colors.RESET}"
        )
        return type_check_exit_code
    print(f"{Colors.GREEN}No Python issues found ✅{Colors.RESET}")
    return 0


def check_templates(args: argparse.Namespace):
    command = f"djlint --profile jinja --check {' '.join(template_paths)}"
    djlint_exit_code = process_run(command, shell=True).returncode
    if djlint_exit_code != 0:
        print(
            f"{Colors.YELLOW}Djlint (Jinja) issues found. Please run 'poetry run check --fix' to fix them, or manually fix them.{Colors.RESET}"
        )
        return djlint_exit_code
    print(f"{Colors.GREEN}No Jinja template issues found ✅{Colors.RESET}")
    return 0


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fix",
        help="Automatically fix linting issues",
        action=argparse.BooleanOptionalAction,
    )

    args = parser.parse_args()

    return check_python(args) or check_templates(args)
