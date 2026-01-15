"""
Poetry script: poetry run check.
Run a bash command to check the project using ruff and djlint.
"""

from subprocess import run as process_run

from scripts.format_templates import template_paths


def check_python():
    paths = ["app", "scripts", "migrations"]
    command = f"ruff check {' '.join(paths)} && ruff format --check {' '.join(paths)}"
    return process_run(command, shell=True).returncode


def check_templates():
    command = f"djlint --profile jinja --check {' '.join(template_paths)}"
    return process_run(command, shell=True).returncode


def run():
    exit_code = check_python()
    exit_code2 = check_templates()
    return exit_code or exit_code2
