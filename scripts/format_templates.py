"""
Poetry script: poetry run format:templates.
Run djlint on all templates to reformat them.
"""

from subprocess import run as process_run

template_paths = [
    "app/cla/templates/*",
    "app/notifications/templates/*",
]


def run():
    command = f"djlint --profile jinja --reformat {' '.join(template_paths)}"
    return process_run(command, shell=True).returncode
