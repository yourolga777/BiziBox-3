"""Тест: устаревшая/чужая ревизия Alembic — БД пересоздаётся заново."""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import _migrate_with_alembic

STALE_REVISION = "d4e5f6a1b2c3"
NEW_HEAD = "a2b3c4d5e6f7"


def _seed_stale_db(sync_url: str) -> None:
    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:r)"),
            {"r": STALE_REVISION},
        )
        # Таблица из прошлой схемы, которой больше нет в моделях.
        conn.execute(
            text("CREATE TABLE categories (id INTEGER PRIMARY KEY, name VARCHAR(255))")
        )
    engine.dispose()


async def test_stale_revision_recreates_schema(db_file, db_url, sync_url) -> None:
    _seed_stale_db(sync_url)

    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    await _migrate_with_alembic(engine)
    await engine.dispose()

    sync = create_engine(sync_url, connect_args={"check_same_thread": False})
    with sync.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    sync.dispose()

    assert rev == NEW_HEAD
    assert "users" in tables
    assert "contacts" in tables
    assert "messages" in tables
    assert "categories" not in tables
