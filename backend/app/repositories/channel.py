from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ChannelModel
from .base import BaseRepository


class ChannelRepository(BaseRepository[ChannelModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(ChannelModel, session, owner_id)

    async def get_connected(self) -> List[ChannelModel]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.is_connected))
        )
        return list(result.scalars().all())

    async def get_disconnected(self) -> List[ChannelModel]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.is_connected.is_(False)))
        )
        return list(result.scalars().all())

    async def get_by_type(self, channel_type: str) -> List[ChannelModel]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.type == channel_type))
        )
        return list(result.scalars().all())
