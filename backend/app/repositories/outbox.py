from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OutboxMessageModel
from .base import BaseRepository


class OutboxRepository(BaseRepository[OutboxMessageModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(OutboxMessageModel, session, owner_id)

    async def get_by_id(self, id: int) -> Optional[OutboxMessageModel]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.id == id))
        )
        return result.scalar_one_or_none()

    async def get_by_client_request_id(
        self, client_request_id: str
    ) -> Optional[OutboxMessageModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.client_request_id == client_request_id,
                    self.model.status != "failed",
                )
            )
        )
        return result.scalars().first()

    async def get_pending(
        self, now: datetime, limit: int = 50
    ) -> List[OutboxMessageModel]:
        query = self._scoped(
            select(self.model)
            .where(
                self.model.status == "pending",
                or_(
                    self.model.next_retry_at.is_(None),
                    self.model.next_retry_at <= now,
                ),
            )
            .order_by(self.model.created_at.asc())
        )
        result = await self.session.execute(query.limit(limit))
        return list(result.scalars().all())

    async def list_by_status(
        self, status: Optional[str], skip: int = 0, limit: int = 200
    ) -> List[OutboxMessageModel]:
        query = self._scoped(
            select(self.model).order_by(self.model.created_at.desc())
        )
        if status:
            query = query.where(self.model.status == status)
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def mark_sent(self, id: int) -> None:
        await self.session.execute(
            self._scoped(
                sql_update(OutboxMessageModel)
                .where(OutboxMessageModel.id == id)
                .values(status="sent", last_error=None, next_retry_at=None)
            )
        )
        await self.session.flush()

    async def mark_failed(self, id: int, error: str) -> None:
        await self.session.execute(
            self._scoped(
                sql_update(OutboxMessageModel)
                .where(OutboxMessageModel.id == id)
                .values(status="failed", last_error=error, next_retry_at=None)
            )
        )
        await self.session.flush()

    async def schedule_retry(
        self,
        id: int,
        attempts: int,
        next_retry_at: datetime,
        error: Optional[str],
    ) -> None:
        await self.session.execute(
            self._scoped(
                sql_update(OutboxMessageModel)
                .where(OutboxMessageModel.id == id)
                .values(
                    status="pending",
                    attempts=attempts,
                    next_retry_at=next_retry_at,
                    last_error=error,
                )
            )
        )
        await self.session.flush()
