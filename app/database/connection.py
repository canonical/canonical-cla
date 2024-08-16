import logging
from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import config

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    config.database.dsn(),
    pool_pre_ping=True,
)


def session_maker():
    return async_sessionmaker(
        bind=async_engine,
        autoflush=False,
        future=True,
        class_=AsyncSession,
    )


async def async_session(
    make_session: Annotated[async_sessionmaker[AsyncSession], Depends(session_maker)]
) -> AsyncIterator[AsyncSession]:
    async with make_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise
