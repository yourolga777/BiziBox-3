import json
from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.task import TaskCommentRepository, TaskRepository
from ..schemas.task import (
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskResponse,
    TaskUpdate,
)


class TaskService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.task_repo = TaskRepository(session, owner_id)

    async def get_all(
        self,
        status: Optional[str] = None,
        contact_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TaskResponse]:
        tasks = await self.task_repo.get_all(
            status=status,
            contact_id=contact_id,
            skip=skip,
            limit=limit,
        )
        return [TaskResponse.model_validate(t) for t in tasks]

    async def get_deleted(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TaskResponse]:
        tasks = await self.task_repo.get_deleted(skip=skip, limit=limit)
        return [TaskResponse.model_validate(t) for t in tasks]

    async def get_by_id(self, task_id: int) -> Optional[TaskResponse]:
        task = await self.task_repo.get_by_id(task_id)
        return TaskResponse.model_validate(task) if task else None

    async def get_detail(self, task_id: int) -> Optional[TaskDetailResponse]:
        task = await self.task_repo.get_detail(task_id)
        if not task:
            return None
        return TaskDetailResponse(
            id=task.id,
            contact_id=task.contact_id,
            contact_name=task.contact.name if task.contact else None,
            message_id=task.message_id,
            title=task.title,
            description=task.description,
            status=task.status,
            due_date=task.due_date,
            reminder_minutes=task.reminder_minutes,
            reminder_at=task.reminder_at,
            recurrence=task.recurrence,
            repeat_dates=json.loads(task.repeat_dates) if task.repeat_dates else None,
            repeat_until=task.repeat_until,
            deleted_at=task.deleted_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            comments=[TaskCommentResponse.model_validate(c) for c in task.comments],
        )

    async def add_comment(self, task_id: int, data: TaskCommentCreate) -> Optional[TaskCommentResponse]:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        comment_repo = TaskCommentRepository(self.session, self.owner_id)
        comment = await comment_repo.create(task_id=task_id, content=data.content)
        return TaskCommentResponse.model_validate(comment)

    async def delete_comment(self, comment_id: int) -> bool:
        comment_repo = TaskCommentRepository(self.session, self.owner_id)
        return await comment_repo.delete(comment_id)

    async def create(self, data: TaskCreate) -> TaskResponse:
        repeat_dates = data.repeat_dates or []
        if not repeat_dates:
            payload = data.model_dump(exclude_unset=True)
            payload.pop("repeat_dates", None)
            task = await self.task_repo.create(**payload)
            return TaskResponse.model_validate(task)
        return await self._create_repeated(data, repeat_dates)

    async def _create_repeated(
        self, data: TaskCreate, repeat_dates: List[str]
    ) -> TaskResponse:
        base_time = data.due_date.time() if data.due_date else time.min
        first: Optional[TaskResponse] = None
        if data.due_date is not None:
            first = await self._create_instance(data, data.due_date)
        for ds in repeat_dates:
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            inst = await self._create_instance(data, datetime.combine(d, base_time))
            if first is None:
                first = inst
        if first is None:
            first = await self._create_instance(data, None)
        return first

    async def _create_instance(
        self, data: TaskCreate, due_date: Optional[datetime]
    ) -> TaskResponse:
        task = await self.task_repo.create(
            title=data.title,
            description=data.description,
            contact_id=data.contact_id,
            message_id=data.message_id,
            due_date=due_date,
            status=data.status,
            reminder_minutes=data.reminder_minutes,
        )
        return TaskResponse.model_validate(task)

    async def update(
        self, task_id: int, data: TaskUpdate
    ) -> Optional[TaskResponse]:
        repeat_dates = data.repeat_dates or []
        if repeat_dates:
            return await self._update_with_repeats(task_id, data, repeat_dates)

        update_dict = data.model_dump(exclude_unset=True)
        update_dict.pop("repeat_dates", None)
        if update_dict.get("status") == "new":
            current = await self.task_repo.get_by_id(task_id)
            if current and current.status == "completed":
                raise ValueError("Completed task cannot be moved back to new")
        task = await self.task_repo.update(task_id, **update_dict)
        return TaskResponse.model_validate(task) if task else None

    async def _update_with_repeats(
        self, task_id: int, data: TaskUpdate, repeat_dates: List[str]
    ) -> Optional[TaskResponse]:
        base_update = data.model_dump(
            exclude_unset=True,
            exclude={"repeat_dates", "recurrence", "repeat_until"},
        )
        task = await self.task_repo.update(task_id, **base_update)
        if task is None:
            return None

        base_time = task.due_date.time() if task.due_date else time.min
        for ds in repeat_dates:
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            await self.task_repo.create(
                title=task.title,
                description=task.description,
                contact_id=task.contact_id,
                due_date=datetime.combine(d, base_time),
                status=task.status,
                reminder_minutes=task.reminder_minutes,
            )
        return TaskResponse.model_validate(task)

    async def delete(self, task_id: int) -> bool:
        return await self.task_repo.soft_delete(task_id)

    async def restore(self, task_id: int) -> Optional[TaskResponse]:
        task = await self.task_repo.restore(task_id)
        return TaskResponse.model_validate(task) if task else None

    async def bulk_delete(self, ids: List[int]) -> int:
        return await self.task_repo.bulk_soft_delete(ids)

    async def bulk_restore(self, ids: List[int]) -> int:
        return await self.task_repo.bulk_restore(ids)

    async def get_pending(self) -> List[TaskResponse]:
        tasks = await self.task_repo.get_by_status('new')
        return [TaskResponse.model_validate(t) for t in tasks]
