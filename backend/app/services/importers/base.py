from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.base import BaseRepository


async def upsert(
    session: AsyncSession,
    repo: BaseRepository[Any], model: Any, old_id: int | None,
    unique_field: str | None, unique_value: Any | None,
    maps: dict[str, dict[int, int]],
    **kwargs: Any,
) -> tuple[int, int]:
    if unique_field and unique_value is not None:
        query = select(model).where(
            getattr(model, unique_field) == unique_value
        )
        if repo.owner_id is not None and hasattr(model, "owner_id"):
            query = query.where(model.owner_id == repo.owner_id)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            await repo.update(existing.id, **kwargs)
            if old_id:
                store_map(maps, model, old_id, existing.id)
            return 0, 1
    created = await repo.create(**kwargs)
    if old_id:
        store_map(maps, model, old_id, created.id)
    return 1, 0


def store_map(maps: dict[str, dict[int, int]], model: Any, old_id: int, new_id: int) -> None:
    key = _model_key(model)
    maps.setdefault(key, {})[old_id] = new_id


def _model_key(model: Any) -> str:
    tablename: str = model.__tablename__
    return tablename


def id_map(maps: dict[str, dict[int, int]], old_id: int | None) -> int | None:
    for m in maps.values():
        if old_id in m:
            return m[old_id]
    return None


def clean(d: dict[str, Any], skip: set[str] | None = None) -> dict[str, Any]:
    if skip is None:
        skip = {"id"}
    cleaned: dict[str, Any] = {}
    for k, v in d.items():
        if k in skip or v is None:
            continue
        if isinstance(v, str):
            try:
                cleaned[k] = datetime.fromisoformat(v)
            except (ValueError, TypeError):
                cleaned[k] = v
        else:
            cleaned[k] = v
    return cleaned
