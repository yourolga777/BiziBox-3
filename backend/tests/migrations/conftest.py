"""Миграционные тесты: прогон Alembic на временных БД + паритет схемы.

Особенности:
- Тесты синхронные (не async): env.py запускает миграции через
  asyncio.run(), внутри async-теста это упадёт.
- БД создаётся во временном файле (tmp_path), settings.DATABASE_URL
  переопределяется на неё — иначе Alembic тронет реальную БД.
- Паритет: отражаем схему БД через sqlalchemy.inspect и сравниваем
  с app.database.Base.metadata (все таблицы, колонки, PK, индексы, FK).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Таблица Alembic не входит в Base.metadata — исключаем из паритета.
_ALEMBIC_TABLES = {"alembic_version"}


def _is_fts_table(name: str) -> bool:
    """FTS5-виртуальная таблица и её shadow-таблицы не входят в Base.metadata."""
    return name == "messages_fts" or name.startswith("messages_fts_")


def make_config(db_url: str) -> Config:
    """Config Alembic с переопределённым URL и script_location."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def run_upgrade(db_url: str, rev: str = "head") -> None:
    import app.config as config_mod

    config_mod.settings.DATABASE_URL = db_url
    command.upgrade(make_config(db_url), rev)


def run_downgrade(db_url: str, rev: str) -> None:
    import app.config as config_mod

    config_mod.settings.DATABASE_URL = db_url
    command.downgrade(make_config(db_url), rev)


def run_stamp(db_url: str, rev: str = "head") -> None:
    import app.config as config_mod

    config_mod.settings.DATABASE_URL = db_url
    command.stamp(make_config(db_url), rev)


def normalize_type(t) -> str:
    """Нормализует строковое представление SQLAlchemy-типа для сравнения."""
    return str(t).split(" COLLATE")[0].strip().upper()


def _metadata_tables():
    from app.database import Base
    from app.models import (  # noqa: F401
        MessageAttachmentModel,
    )

    return Base.metadata.tables


def compare_schema(db_url: str) -> None:
    """Сравнивает фактическую схему БД с Base.metadata."""
    from app.database import Base

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    insp = inspect(engine)

    actual = {t for t in insp.get_table_names() if not _is_fts_table(t)}
    expected = set(Base.metadata.tables.keys())
    assert actual == expected | _ALEMBIC_TABLES, (
        f"Расхождение набора таблиц: actual={sorted(actual - _ALEMBIC_TABLES)}, "
        f"expected={sorted(expected)}"
    )

    for table_name in sorted(expected):
        meta = Base.metadata.tables[table_name]

        act_cols = {c["name"]: c for c in insp.get_columns(table_name)}
        exp_cols = {c.name: c for c in meta.columns}

        assert set(act_cols) == set(exp_cols), (
            f"[{table_name}] колонки: actual={sorted(act_cols)} expected={sorted(exp_cols)}"
        )

        for name, act in act_cols.items():
            exp = exp_cols[name]
            assert normalize_type(act["type"]) == normalize_type(exp.type), (
                f"[{table_name}.{name}] тип: actual={normalize_type(act['type'])} "
                f"expected={normalize_type(exp.type)}"
            )

        act_pk = set(insp.get_pk_constraint(table_name)["constrained_columns"] or [])
        exp_pk = {c.name for c in meta.primary_key.columns}
        assert act_pk == exp_pk, f"[{table_name}] PK: actual={act_pk} expected={exp_pk}"

        act_idx = {
            (ix["name"], tuple(ix["column_names"]), bool(ix["unique"]))
            for ix in insp.get_indexes(table_name)
        }
        exp_idx = set()
        for idx in meta.indexes:
            exp_idx.add(
                (
                    idx.name,
                    tuple(c.name for c in idx.columns),
                    bool(idx.unique),
                )
            )
        assert act_idx == exp_idx, f"[{table_name}] индексы: actual={act_idx} expected={exp_idx}"

        act_fk = {
            (
                tuple(fk["constrained_columns"]),
                fk["referred_table"],
                tuple(fk["referred_columns"]),
            )
            for fk in insp.get_foreign_keys(table_name)
        }
        exp_fk = {
            ((fk.parent.name,), fk.column.table.name, (fk.column.name,))
            for fk in meta.foreign_keys
        }
        assert act_fk == exp_fk, f"[{table_name}] FK: actual={act_fk} expected={exp_fk}"

    engine.dispose()


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return tmp_path / "migrate.db"


@pytest.fixture
def db_url(db_file: Path) -> str:
    # aiosqlite — Alembic env.py использует async-движок.
    return f"sqlite+aiosqlite:///{db_file.as_posix()}"


@pytest.fixture
def sync_url(db_file: Path) -> str:
    # sync-движок для sqlalchemy.inspect / прямых запросов.
    return f"sqlite:///{db_file.as_posix()}"


@pytest.fixture
def run_head(db_url: str) -> Callable[[], None]:
    def _run() -> None:
        run_upgrade(db_url, "head")

    return _run
