import asyncio
from logging.config import fileConfig
from sqlite3 import OperationalError

from alembic import context
from asyncpg import InvalidCatalogNameError
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

from database import async_engine


async def create_database_if_not_exists(engine: AsyncEngine):
    """Check if a database exists.

    :param url: A SQLAlchemy engine URL.
    """

    url = make_url(engine.url)
    database = url.database
    dialect_name = url.get_dialect().name
    if dialect_name != 'postgresql':
        raise NotImplementedError(
            'create_database_if_not_exists is only implemented for PostgreSQL'
        )
    try:
        connection = await engine.connect()
    except InvalidCatalogNameError as e:
        if not 'does not exist' in str(e):
            raise
    else:
        await connection.close()
        return
    # create the database
    url = url._replace(database='postgres')
    engine2 = create_async_engine(url)
    missing_database = database
    template = 'template1'
    async with engine2.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        create_db_query = "CREATE DATABASE \"{}\" ENCODING '{}' TEMPLATE {}".format(
            missing_database,
            'utf8',
            template
        )
        await conn.execute(text(create_db_query))
    await engine2.dispose()


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def include_object(obj, name, type_, reflected, compare_to):
    if obj.info.get("skip_autogen", False):
        return False

    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = "sqlite:///db.sqlite"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine

    # Ensure the database exists before running migrations
    await create_database_if_not_exists(async_engine)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
