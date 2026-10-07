from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models import TaskCommentModel, TaskModel
from .base import BaseRepository


class TaskCommentRepository(BaseRepository[TaskCommentModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(TaskCommentModel, session, owner_id)

    async def get_by_task(self, task_id: int) -> List[TaskCommentModel]:
        result = await self.session.execute(
            self._scoped(
                select(TaskCommentModel)
                .where(TaskCommentModel.task_id == task_id)
                .order_by(TaskCommentModel.created_at)
            )
        )
        return list(result.scalars().all())


class TaskRepository(BaseRepository[TaskModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(TaskModel, session, owner_id)

    async def get_all(  # type: ignore[override]
        self,
        status: Optional[str] = None,
        contact_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[TaskModel]:
        query = self._scoped(select(self.model).order_by(self.model.created_at.desc()))
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        if status:
            query = query.where(self.model.status == status)
        if contact_id:
            query = query.where(self.model.contact_id == contact_id)
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_deleted(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.deleted_at.is_not(None))
                .order_by(self.model.deleted_at.desc())
                .offset(skip).limit(limit)
            )
        )
        return list(result.scalars().all())

    async def soft_delete(self, task_id: int) -> bool:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.id == task_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return False
        task.deleted_at = datetime.utcnow()
        return True

    async def restore(self, task_id: int) -> Optional[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.id == task_id,
                    self.model.deleted_at.is_not(None),
                )
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        task.deleted_at = None
        return task

    async def bulk_soft_delete(self, ids: List[int]) -> int:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.id.in_(ids),
                    self.model.deleted_at.is_(None),
                )
            )
        )
        tasks = result.scalars().all()
        now = datetime.utcnow()
        for task in tasks:
            task.deleted_at = now
        return len(tasks)

    async def bulk_restore(self, ids: List[int]) -> int:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.id.in_(ids),
                    self.model.deleted_at.is_not(None),
                )
            )
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.deleted_at = None
        return len(tasks)

    async def get_by_contact(self, contact_id: int) -> List[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.contact_id == contact_id,
                    self.model.deleted_at.is_(None),
                )
                .order_by(self.model.created_at.desc())
            )
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> List[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.status == status,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def get_recurring(self) -> List[TaskModel]:
        """Повторяющиеся задачи (с due_date), для раскрытия в календаре."""
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.deleted_at.is_(None),
                    self.model.due_date.is_not(None),
                    self.model.recurrence.is_not(None),
                )
                .options(joinedload(self.model.contact))
                .order_by(self.model.due_date)
            )
        )
        return list(result.scalars().all())

    async def get_pending(self) -> List[TaskModel]:
        """Устаревший alias для get_by_status('new')."""
        return await self.get_by_status("new")

    async def get_detail(self, task_id: int) -> Optional[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.id == task_id,
                    self.model.deleted_at.is_(None),
                )
                .options(
                    joinedload(self.model.contact),
                    joinedload(self.model.comments),
                )
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> List[TaskModel]:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.deleted_at.is_(None),
                    self.model.due_date.is_not(None),
                    self.model.due_date >= start_dt,
                    self.model.due_date <= end_dt,
                )
                .options(joinedload(self.model.contact))
                .order_by(self.model.due_date)
            )
        )
        return list(result.scalars().all())

    async def get_reminder_candidates(self) -> List[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.deleted_at.is_(None),
                    self.model.due_date.is_not(None),
                    self.model.reminder_minutes.is_not(None),
                    self.model.last_reminded_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def get_fired_reminders(self, limit: int = 50) -> List[TaskModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(
                    self.model.deleted_at.is_(None),
                    self.model.last_reminded_at.is_not(None),
                    self.model.reminder_seen_at.is_(None),
                )
                .order_by(self.model.last_reminded_at.desc())
                .limit(limit)
            )
        )
        return list(result.scalars().all())

    async def mark_reminded(self, ids: List[int], reminded_at: datetime) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(TaskModel)
                .where(TaskModel.id.in_(ids))
                .values(last_reminded_at=reminded_at)
            )
        )
        await self.session.flush()
        return result.rowcount

    async def mark_reminder_seen(self, task_id: int) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(TaskModel)
                .where(TaskModel.id == task_id)
                .values(reminder_seen_at=datetime.now())
            )
        )
        await self.session.flush()
        return result.rowcount
