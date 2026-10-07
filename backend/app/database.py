import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .db_functions import register_sqlite_functions
from .paths import ensure_bundle_importable, get_bundle_dir, get_data_dir
from .user_context import get_active_login, get_user_db_url

logger = logging.getLogger(__name__)

_BUNDLE_DIR = get_bundle_dir()
_DATA_DIR = get_data_dir()
_ALEMBIC_INI = _BUNDLE_DIR / "alembic.ini"
_MIGRATIONS_DIR = _BUNDLE_DIR / "migrations"
_BACKUP_DIR = _DATA_DIR / "backup"
_BACKUP_KEEP = 5

# Engine registry keyed by login. Tests can override the module-level
# ``engine`` and ``AsyncSessionLocal`` attributes directly (see conftest.py).
_engine_registry: dict[str, AsyncEngine] = {}


class Base(DeclarativeBase):
    pass


# Test overrides. Keep these names stable; conftest.py patches them.
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine(login: str | None = None) -> AsyncEngine:
    """Return the async engine for *login* (or the active login).

    Falls back to the module-level ``engine`` override when set (tests).
    """
    if engine is not None:
        return engine

    if login is None:
        login = get_active_login()
    if login is None:
        raise RuntimeError("No active user login; cannot create database engine")

    if login not in _engine_registry:
        url = get_user_db_url(login)
        eng = create_async_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        event.listen(eng.sync_engine, "connect", register_sqlite_functions)
        _engine_registry[login] = eng
    return _engine_registry[login]


def get_async_session_maker(login: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Return an async session maker for *login* (or the active login)."""
    if AsyncSessionLocal is not None:
        return AsyncSessionLocal
    return async_sessionmaker(
        get_engine(login),
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _alembic_config(url: str | None = None) -> Config:
    """Alembic Config: URL берётся из переданного значения или settings.DATABASE_URL."""
    ensure_bundle_importable()
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", url or settings.DATABASE_URL)
    return cfg


def _db_file_path(eng: AsyncEngine) -> Path | None:
    """Путь к файлу БД из URL движка, или None для in-memory / не файловой БД."""
    url = str(eng.url)
    if not url.startswith(("sqlite:///", "sqlite+aiosqlite:///")):
        return None
    path = url.split(":///", 1)[1]
    if ":memory:" in path or not path:
        return None
    path = path.split("?", 1)[0]
    db_path = Path(path)
    if not db_path.is_absolute():
        db_path = (_DATA_DIR / db_path).resolve()
    return db_path


def _backup_database(eng: AsyncEngine) -> None:
    """Копирует файл БД в data/backup с таймстампом (ротация _BACKUP_KEEP)."""
    db_path = _db_file_path(eng)
    if db_path is None or not db_path.exists():
        return
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = _BACKUP_DIR / f"bizibox-{ts}.db"
    shutil.copy2(db_path, dst)
    logger.info("DB backup created: %s", dst)

    backups = sorted(_BACKUP_DIR.glob("bizibox-*.db"))
    for old in backups[: max(0, len(backups) - _BACKUP_KEEP)]:
        old.unlink(missing_ok=True)


def _current_revision(conn: Connection) -> str | None:
    """Текущая ревизия Alembic из alembic_version, или None.

    None означает: таблицы alembic_version нет либо она пуста (БД не под
    управлением Alembic — legacy, созданная create_all/вручную).
    Вызывается через run_sync: получает синхронное подключение.
    """
    from sqlalchemy import inspect

    insp = inspect(conn)
    if insp is None or not insp.has_table("alembic_version"):
        return None
    return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


async def _run_migrations_in_thread(url: str) -> None:
    """Запускает Alembic upgrade в отдельном потоке.

    env.py выполняет asyncio.run() — нельзя из запущенного event loop.
    """

    async def _worker() -> None:
        await asyncio.to_thread(lambda: command.upgrade(_alembic_config(url), "head"))

    await _worker()


def _revision_in_chain(url: str, revision: str) -> bool:
    """True, если *revision* присутствует в текущей цепочке миграций."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config(url))
    try:
        return script.get_revision(revision) is not None
    except Exception:
        return False


async def _drop_all_tables(eng: AsyncEngine) -> None:
    """Удаляет все таблицы из файловой БД (в т.ч. устаревшие/чужие)."""
    async with eng.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        )
        for row in result:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{row[0]}"'))


async def _migrate_with_alembic(eng: AsyncEngine) -> None:
    """Прогон Alembic для существующей файловой БД."""
    url = str(eng.url)
    async with eng.connect() as conn:
        revision = await conn.run_sync(_current_revision)

    if revision:
        if _revision_in_chain(url, revision):
            await _run_migrations_in_thread(url)
            return
        # Ревизия из старого/чужого проекта (например, БД BiziBox до форка) —
        # миграции на неё не знают. Пересоздаём схему заново.
        logger.warning(
            "Stale Alembic revision %r not in current chain — recreating DB schema",
            revision,
        )
        await _drop_all_tables(eng)
        await _run_migrations_in_thread(url)
        return

    async with eng.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        )
        tables = {row[0] for row in result}
    business_tables = tables - {"alembic_version"}

    if business_tables:
        logger.info("Legacy DB detected (%d tables), stamping head", len(business_tables))
        await asyncio.to_thread(lambda: command.stamp(_alembic_config(url), "head"))
    else:
        await _run_migrations_in_thread(url)


async def init_db(login: str | None = None, clear_first: bool = False) -> None:
    """Инициализирует БД пользователя *login* (или активного пользователя)."""
    eng = get_engine(login)

    if not clear_first:
        _backup_database(eng)
        async with eng.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=5000"))
        await _migrate_with_alembic(eng)
        from .services.seed_service import seed_default_type_templates

        async with eng.begin() as conn:
            await conn.run_sync(seed_default_type_templates)
        return

    from .services.seed_service import (
        seed_default_folders,
        seed_default_owner,
        seed_default_type_templates,
    )

    async with eng.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            try:
                await conn.execute(table.delete())
            except Exception:
                pass
        await conn.run_sync(seed_default_owner)
        await conn.run_sync(seed_default_folders)
        await conn.run_sync(seed_default_type_templates)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
