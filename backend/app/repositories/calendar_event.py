from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models import CalendarEventModel
from .base import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEventModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(CalendarEventModel, session, owner_id)

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[CalendarEventModel]:
        query = self._scoped(
            select(self.model)
            .order_by(self.model.date, self.model.time)
            .options(joinedload(self.model.contact))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_detail(self, event_id: int) -> Optional[CalendarEventModel]:
        query = self._scoped(
            select(self.model)
            .where(self.model.id == event_id)
            .options(joinedload(self.model.contact))
        )
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[CalendarEventModel]:
        query = self._scoped(
            select(self.model)
            .where(
                self.model.date >= start_date,
                self.model.date <= end_date,
            )
            .order_by(self.model.date, self.model.time)
            .options(joinedload(self.model.contact))
        )
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_recurring(self) -> List[CalendarEventModel]:
        """Повторяющиеся события для раскрытия в календаре."""
        query = self._scoped(
            select(self.model)
            .where(self.model.recurrence.is_not(None))
            .order_by(self.model.date, self.model.time)
            .options(joinedload(self.model.contact))
        )
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_reminder_candidates(self) -> List[CalendarEventModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.reminder_minutes.is_not(None),
                    self.model.last_reminded_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def mark_reminded(self, ids: List[int], reminded_at: datetime) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(CalendarEventModel)
                .where(CalendarEventModel.id.in_(ids))
                .values(last_reminded_at=reminded_at)
            )
        )
        await self.session.flush()
        return result.rowcount

    async def get_fired_reminders(self, limit: int = 50) -> List[CalendarEventModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.last_reminded_at.is_not(None),
                    self.model.reminder_seen_at.is_(None),
                )
                .order_by(self.model.last_reminded_at.desc())
                .limit(limit)
            )
        )
        return list(result.scalars().all())

    async def mark_reminder_seen(self, event_id: int) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(CalendarEventModel)
                .where(CalendarEventModel.id == event_id)
                .values(reminder_seen_at=datetime.now())
            )
        )
        await self.session.flush()
        return result.rowcount
