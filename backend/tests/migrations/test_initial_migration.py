"""Тесты initial-миграции BiziBox: fresh-DB upgrade head + паритет схемы + seed."""
from sqlalchemy import create_engine, text

from .conftest import compare_schema, run_downgrade, run_upgrade


def test_initial_migration_schema_parity(db_url: str, sync_url: str) -> None:
    run_upgrade(db_url, "head")
    compare_schema(sync_url)


def test_initial_migration_seeds_owner_and_folders(db_url: str, sync_url: str) -> None:
    run_upgrade(db_url, "head")

    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        owner = conn.execute(
            text("SELECT username FROM users WHERE id = 1")
        ).scalar_one()
        folders = conn.execute(
            text(
                "SELECT category_key FROM contact_folders "
                "WHERE is_default = 1 ORDER BY sort_order"
            )
        ).scalars().all()
    engine.dispose()

    assert owner == "owner"
    assert sorted(folders) == ["customers", "employees", "family", "friends", "groups", "service", "study", "suppliers"]


def test_initial_migration_seed_idempotent(db_url: str, sync_url: str) -> None:
    run_upgrade(db_url, "head")
    run_upgrade(db_url, "head")

    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        folder_count = conn.execute(
            text("SELECT COUNT(*) FROM contact_folders")
        ).scalar_one()
        owner_count = conn.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar_one()
    engine.dispose()

    assert folder_count == 8
    assert owner_count == 1


def test_initial_migration_downgrade_cleans(db_url: str, sync_url: str) -> None:
    run_upgrade(db_url, "head")
    run_downgrade(db_url, "base")

    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ).scalars().all()
    engine.dispose()

    # После downgrade до base остаётся только служебная таблица alembic_version.
    assert tables == ["alembic_version"]
