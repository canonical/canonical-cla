"""
Poetry script: poetry run format.
Run a bash command to format the project using black and isort.
"""

from subprocess import run as process_run


def run():
    paths = ["app", "scripts", "migrations"]
    command = f"isort {' '.join(paths)} && black {' '.join(paths)}"
    process_run(command, shell=True)
