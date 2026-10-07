from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ContactFolderModel
from .base import BaseRepository


class ContactFolderRepository(BaseRepository[ContactFolderModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(ContactFolderModel, session, owner_id)

    async def get_all(
        self, skip: int = 0, limit: Optional[int] = 100
    ) -> List[ContactFolderModel]:
        query = self._scoped(
            select(self.model).order_by(self.model.sort_order, self.model.name)
        )
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_by_category_key(self, category_key: str) -> List[ContactFolderModel]:
        query = self._scoped(
            select(self.model).where(self.model.category_key == category_key)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
