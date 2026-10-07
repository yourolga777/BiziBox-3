"""Тесты для include_object_filter в migrations/env_filter.py."""
from migrations.env_filter import include_object_filter


def test_include_object_filter_ignores_legacy_and_auto_indexes() -> None:
    """idx_* (legacy) и ix_* (auto-generated SQLAlchemy) игнорируются autogenerate."""
    assert include_object_filter(None, "idx_foo", "index", False, None) is False
    assert include_object_filter(None, "ix_foo", "index", False, None) is False


def test_include_object_filter_keeps_real_indexes() -> None:
    """Реальные именованные unique-индексы и прочие объекты не игнорируются."""
    assert include_object_filter(None, "uq_foo", "index", False, None) is True
    assert include_object_filter(None, "pk_foo", "index", False, None) is True


def test_include_object_filter_ignores_reflected_tables_without_model() -> None:
    """Reflected-таблицы, отсутствующие в metadata, не предлагаются к удалению."""
    assert include_object_filter(None, "orphan_table", "table", True, None) is False


def test_include_object_filter_keeps_real_tables() -> None:
    """Обычные таблицы не игнорируются."""
    assert include_object_filter(None, "users", "table", False, object()) is True
