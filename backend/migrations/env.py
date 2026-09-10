import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure the src directory is on sys.path so we can import the project
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from forge.infrastructure.persistence import models  # noqa: F401, E402 - ensures all models are imported
from forge.infrastructure.persistence.models import Base  # noqa: E402 - import must follow app path setup above

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Alembic 默认自建版本表的 version_num 列为 VARCHAR(32)，本项目长 revision id
    # （如 "0030_users_pet_profiles_id_defaults" 共 35 字符）会触发
    # StringDataRightTruncationError，导致空库 upgrade head 断在 0030。
    # 此处预建加宽版本表（已存在则跳过），替代历史“手工预建 alembic_version”步骤。
    async with connectable.begin() as conn:
        has_version_table = await conn.run_sync(lambda sc: sa_inspect(sc).has_table("alembic_version"))
        if not has_version_table:
            await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL)"))
            await conn.execute(text("CREATE UNIQUE INDEX ix_alembic_version ON alembic_version (version_num)"))

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
