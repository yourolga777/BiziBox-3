from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ImportMappingModel
from .base import BaseRepository


class ImportMappingRepository(BaseRepository[ImportMappingModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(ImportMappingModel, session, owner_id)

    async def get_by_file_pattern(self, pattern: str) -> Optional[ImportMappingModel]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.file_pattern == pattern))
        )
        return result.scalar_one_or_none()
