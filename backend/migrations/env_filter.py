"""Фильтр autogenerate для migrations/env.py.

Вынесен в отдельный модуль, чтобы быть импортируемым без инициализации
Alembic-контекста (нужно для тестов).
"""
from typing import Any


def include_object_filter(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Фильтр autogenerate: игнорировать авто-индексы и reflected-таблицы.

    - Авто-индексы SQLAlchemy (`ix_*`) генерируются из `index=True` моделей
      и не должны предлагаться autogenerate как новые/удалённые.
    - Legacy-индексы (`idx_*`) предшествуют стандартному именованию `ix_*`;
      они игнорируются, чтобы autogenerate не предлагал их удаление.
    - Таблицы, существующие в БД, но отсутствующие в metadata (reflected),
      не должны предлагаться к удалению.
    """
    if type_ == "index" and name is not None and (
        name.startswith("ix_") or name.startswith("idx_")
    ):
        return False
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True
