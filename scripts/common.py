import inspect
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any

from fastapi import Request
from fastapi.datastructures import State
from fastapi.dependencies.utils import get_dependant, solve_dependencies

from app.middlewares import request_ip_address_context_var


def create_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
    return logger


logger = create_logger("common")


async def run_command(command: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Given a callable, will solve its dependencies and run it with provided args and kwargs."""
    setup_environment()
    if len(args) > 0:
        raise ValueError("Positional arguments are not supported")
    async with AsyncExitStack() as cm:
        query = {}
        for key, value in kwargs.items():
            query[key] = value

        query_string = "&".join([f"{key}={value}" for key, value in query.items()])

        request = Request(
            {
                "type": "http",
                "headers": [],
                "query_string": query_string.encode(),
                "fastapi_astack": cm,
                "state": State(),
            }
        )

        dependant = get_dependant(path="command", call=command)

        (
            solved_kwargs,
            errors,
            background_tasks,
            sub_concurrency_limits,
            dependency_overrides_provider,
        ) = await solve_dependencies(
            request=request,
            dependant=dependant,
            body=None,
            background_tasks=None,
            response=None,
            dependency_overrides_provider=None,
            async_exit_stack=cm,
        )

        if errors:
            raise Exception(f"Dependency solving errors: {errors}")
        if not dependant.call:
            raise ValueError("Could not find a callable to run")

        if inspect.iscoroutinefunction(dependant.call):
            result = await dependant.call(**solved_kwargs)
        else:
            result = dependant.call(**solved_kwargs)

        return result


def setup_environment():
    """Set up the environment for the interactive shell."""

    # set request's ip as it is required by the audit log
    request_ip_address_context_var.set("127.0.0.1")

    pythonpath = os.environ.get("PYTHONPATH", "")
    additional_path = "/usr/lib/python3.10/site-packages"
    if pythonpath:
        os.environ["PYTHONPATH"] = f"{pythonpath}:{additional_path}"
    else:
        os.environ["PYTHONPATH"] = additional_path
    # In production, find the existing uvicorn process and use its environment variables
    try:
        user_id = os.getuid()
        result = subprocess.run(
            ["pgrep", "-u", str(user_id), "-f", "uvicorn"],
            capture_output=True,
            text=True,
            check=True,
        )

        pids = result.stdout.strip().split("\n")
        if not pids or not pids[0]:
            logger.warning("No uvicorn process found for current user")
            return

        pid = pids[0]
        logger.info(f"Found uvicorn process with PID: {pid}")

        # Read environment variables from /proc/<pid>/environ
        environ_path = f"/proc/{pid}/environ"
        if not os.path.exists(environ_path):
            logger.warning(f"Environment file not found: {environ_path}")
            return

        with open(environ_path, "rb") as f:
            environ_data = f.read()

        # Parse null-delimited environment variables
        # Split by null byte and filter out empty strings
        env_vars = [var.decode("utf-8") for var in environ_data.split(b"\x00") if var]

        # Set environment variables
        for env_var in env_vars:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                os.environ[key] = value

        logger.info(
            f"Loaded {len(env_vars)} environment variables from uvicorn process"
        )

        logger.info("Environment setup complete")

    except subprocess.CalledProcessError:
        logger.warning("Could not find uvicorn process using pgrep")
    except FileNotFoundError:
        logger.warning("pgrep command not found. Make sure you're on a Linux system.")
    except Exception as e:
        logger.error(f"Error setting up environment: {e}", exc_info=True)


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
