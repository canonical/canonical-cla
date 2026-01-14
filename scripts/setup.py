"""
Poetry script: poetry run setup.
Set up the development environment including pre-commit hooks.
"""

from subprocess import run as process_run


def run():
    """Install pre-commit hooks."""
    command = "pre-commit install"
    exit_code = process_run(command, shell=True).returncode
    if exit_code == 0:
        print("✓ Pre-commit hooks installed successfully")
    else:
        print("✗ Failed to install pre-commit hooks")
    return exit_code
