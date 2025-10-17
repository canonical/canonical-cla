"""
Poetry script: poetry run dev.
Run a bash command to start the app in development mode.
"""

from subprocess import run as process_run


def run():
    command = "uvicorn app.main:app --reload"
    exit(process_run(command, shell=True).returncode)
