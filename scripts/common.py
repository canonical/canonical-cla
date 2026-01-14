import inspect
import logging
import sys
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any

from fastapi import Request
from fastapi.datastructures import State
from fastapi.dependencies.utils import get_dependant, solve_dependencies


async def run_command(command: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Given a callable, will solve its dependencies and run it with provided args and kwargs."""
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


def create_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
    return logger
