"""
Poetry script: poetry run test.
Run a bash command to run the unit tests using pytest.
"""

import argparse
from subprocess import run as process_run


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coverage",
        help="Generate a coverage report",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--show-capture",
        help="Show stdout/stderr capture output on test failure",
        action=argparse.BooleanOptionalAction,
    )

    args = parser.parse_args()

    command: str
    if args.coverage:
        command = "&&".join(
            [
                "coverage run -m pytest",
                "echo ' ============================== '",
                "echo ' =      Coverage Report       = '",
                "echo ' ============================== '",
                "coverage report",
            ]
        )
    else:
        command = "pytest" + (" -s" if args.show_capture else "")
    exit(process_run(command, shell=True).returncode)
