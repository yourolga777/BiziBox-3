import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base
from app.models import *  # noqa: F403
from migrations.env_filter import include_object_filter

config = context.config

if config.config_file_name is not None:
    # fileConfig переписывает root-логгер (уровень WARN + console-хендлер из
    # alembic.ini). В рантайме приложения это снимает RotatingFileHandler и
    # глушит INFO-логи в bizibox.log — поэтому сохраняем настройки приложения.
    root_logger = logging.getLogger()
    _saved_level = root_logger.level
    _saved_handlers = list(root_logger.handlers)
    _saved_propagate = root_logger.propagate
    fileConfig(config.config_file_name, disable_existing_loggers=False)
    if _saved_handlers:
        root_logger.setLevel(_saved_level)
        root_logger.handlers = _saved_handlers
        root_logger.propagate = _saved_propagate
    logging.getLogger("alembic").setLevel(logging.INFO)

# sqlalchemy.url берётся из alembic Config (устанавливается database.py)
# либо из settings.DATABASE_URL для CLI/CI (R1-10 AC).
config.set_main_option(
    "sqlalchemy.url",
    config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_object=include_object_filter,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        # compare_server_default намеренно не включён: известен ложными
        # срабатываниями на server_default для DateTime (см. R1-10 AC5).
        include_object=include_object_filter,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
