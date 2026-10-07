from typing import Any, Dict, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.settings import SettingsModel

S = TypeVar("S")


class SettingsRepository:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id

    def _scoped(self, stmt: S) -> S:
        if self.owner_id is not None:
            stmt = stmt.where(SettingsModel.owner_id == self.owner_id)  # type: ignore[attr-defined]
        return stmt

    async def get_all(self) -> Dict[str, Any]:
        result = await self.session.execute(self._scoped(select(SettingsModel)))
        rows = result.scalars().all()
        return {str(row.key): row.value for row in rows}

    async def get(self, key: str) -> Optional[Any]:
        result = await self.session.execute(
            self._scoped(select(SettingsModel).where(SettingsModel.key == key))
        )
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def set(self, key: str, value: Any) -> SettingsModel:
        existing = await self.session.execute(
            self._scoped(select(SettingsModel).where(SettingsModel.key == key))
        )
        row = existing.scalar_one_or_none()
        if row:
            row.value = value
        else:
            row = SettingsModel(key=key, value=value)
            if self.owner_id is not None:
                row.owner_id = self.owner_id
            self.session.add(row)
        await self.session.flush()
        return row

    async def set_many(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            await self.set(key, value)
