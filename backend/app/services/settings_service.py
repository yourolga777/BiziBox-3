from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.settings import SettingsRepository


async def get_poll_interval(
    session: AsyncSession,
    key: str,
    default: int,
    owner_id: Optional[int] = None,
) -> int:
    """Возвращает интервал опроса из БД (если сохранён), иначе конфиг-дефолт."""
    repo = SettingsRepository(session, owner_id)
    value = await repo.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class SettingsService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.owner_id = owner_id
        self.repo = SettingsRepository(session, owner_id)

    async def get_all(self) -> Dict[str, Any]:
        return await self.repo.get_all()

    async def get(self, key: str) -> Any:
        return await self.repo.get(key)

    async def set(self, key: str, value: Any) -> None:
        await self.repo.set(key, value)

    async def set_many(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            await self.repo.set(key, value)

    async def ensure_defaults(self, defaults: Dict[str, Any]) -> None:
        for key, value in defaults.items():
            existing = await self.repo.get(key)
            if existing is None:
                await self.repo.set(key, value)
