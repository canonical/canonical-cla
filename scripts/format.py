"""
Poetry script: poetry run check.
Run a bash command to check the project using ruff and djlint.
"""

from subprocess import run as process_run


def run():
    return process_run("poetry run check --fix", shell=True).returncode
