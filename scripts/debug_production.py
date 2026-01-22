#!/usr/bin/env python3
"""
A CLI script to be run with Bash to import contributors from a JSON file.
Make sure environment variables are set before running this script.


while read -rd $'\0' line; do export "$line"; done < /proc/$(pgrep -u $(id -u) -f uvicorn)/environ
export PYTHONPATH=$PYTHONPATH:/usr/lib/python3.10/site-packages
"""

from app.http_client import HTTPClient, http_client

import asyncio
from fastapi import Depends
from scripts.common import create_logger, run_command

logger = create_logger("import_contributors")


async def remove_old_contributors(http_client: HTTPClient = Depends(http_client)):
    """
    Import contributors from a JSON file.
    """
    github_api_response = await http_client.get(url="https://api.github.com/")
    print(github_api_response.json())

    response = await http_client.get(
        url="https://login.staging.canonical.com/.well-known/openid-configuration"
    )

    print(response.json())



def main():
    asyncio.run(run_command(remove_old_contributors))


if __name__ == "__main__":
    main()
