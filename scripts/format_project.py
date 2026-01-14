"""
Poetry script: poetry run format.
Run a bash command to format the project using ruff.
"""

from subprocess import run as process_run

from scripts.format_templates import run as format_templates


def format_python():
    paths = ["app", "scripts", "migrations"]
    command = f"ruff check --fix {' '.join(paths)} && ruff format {' '.join(paths)}"
    return process_run(command, shell=True).returncode


def run():
    exit_code = format_python()
    exit_code2 = format_templates()
    return exit_code or exit_code2
