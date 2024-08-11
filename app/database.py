import logging
from typing import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import config

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    config.database.dsn(),
    pool_pre_ping=True,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async_session = async_sessionmaker(
        bind=async_engine,
        autoflush=False,
        future=True,
    )
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise


redis = Redis.from_url(config.redis.dsn())
