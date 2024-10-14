#!/usr/bin/env python3
"""
A CLI script to be run with Bash to import contributors from a JSON file.
Make sure environment variables are set before running this script.
"""

import argparse
import asyncio
import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import AuditLog, Individual
from scripts.common import create_logger, run_command

logger = create_logger("import_contributors")


async def get_audit_logs(
    session: Annotated[AsyncSession, Depends(async_session)],
    since: datetime.datetime,
    until: datetime.datetime,
):
    """
    Import contributors from a JSON file.
    """
    query = select(AuditLog)
    query = query.where(AuditLog.timestamp >= since)
    query = query.where(AuditLog.timestamp < until)
    print(since, until)
    result = await session.execute(query)
    audit_logs = result.scalars().all()
    for log in audit_logs:
        print(log)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--since",
        help="JSON file with contributors (optional, default: yesterday), format: YYYY-MM-DD",
        type=str,
        required=False,
        default=(datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d"
        ),
    )
    arg_parser.add_argument(
        "--until",
        help="JSON file with contributors (optional, default: now), format: YYYY-MM-DD",
        type=str,
        required=False,
        default=datetime.datetime.now().strftime("%Y-%m-%d"),
    )
    args = arg_parser.parse_args()
    since = datetime.datetime.strptime(args.since, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    until = datetime.datetime.strptime(args.until, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    asyncio.run(run_command(get_audit_logs, since=since, until=until))


if __name__ == "__main__":
    main()
