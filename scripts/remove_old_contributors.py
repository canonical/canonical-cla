#!/usr/bin/env python3
"""
A CLI script to be run with Bash to import contributors from a JSON file.
Make sure environment variables are set before running this script.
"""

import asyncio
import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import Individual
from scripts.common import create_logger, run_command

logger = create_logger("import_contributors")


async def remove_old_contributors(
    session: Annotated[AsyncSession, Depends(async_session)],
):
    """
    Import contributors from a JSON file.
    """
    query = select(Individual)
    query = query.where(Individual.signed_at < datetime.datetime(2024, 10, 1, 0, 0, 0))
    result = await session.execute(query)
    old_contributors = result.scalars().all()
    logger.info(f"Removing {len(old_contributors)} old contributors...")
    for contributor in old_contributors:
        await session.delete(contributor)
    await session.commit()
    logger.info(f"Removed {len(old_contributors)} old contributors.")


def main():
    asyncio.run(run_command(remove_old_contributors))


if __name__ == "__main__":
    main()
