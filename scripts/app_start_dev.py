"""
Poetry script: poetry run dev.
Run a bash command to start the app in development mode.
"""

from subprocess import run as process_run


def run():
    command = "fastapi dev app/main.py"
    process_run(command, shell=True)
