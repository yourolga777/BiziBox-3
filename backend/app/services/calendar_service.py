from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CalendarEventModel, ContactModel
from ..repositories.calendar_event import CalendarEventRepository
from ..repositories.task import TaskRepository
from ..schemas.calendar import (
    CalendarEvent,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
)


def _add_months(d: date, months: int) -> date:
    import calendar as _cal

    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    last_day = _cal.monthrange(year, month)[1]
    return d.replace(year=year, month=month, day=min(d.day, last_day))


def _recurrence_dates(
    base_date: date,
    recurrence: Optional[str],
    start_date: date,
    end_date: date,
    until: Optional[date] = None,
) -> List[date]:
    limit = min(end_date, until) if until is not None else end_date
    if not recurrence or recurrence not in ("daily", "weekly", "monthly"):
        return [base_date] if start_date <= base_date <= limit else []

    step_days: Optional[int] = {"daily": 1, "weekly": 7}.get(recurrence)

    results: List[date] = []
    cur = base_date
    guard = 0
    while cur <= limit and guard < 1000:
        if cur >= start_date:
            results.append(cur)
        guard += 1
        if step_days is not None:
            cur = cur + timedelta(days=step_days)
        else:
            cur = _add_months(cur, 1)
    return results


class CalendarService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.task_repo = TaskRepository(session, owner_id)
        self.event_repo = CalendarEventRepository(session, owner_id)

    async def get_events(
        self,
        start_date: date,
        end_date: date,
    ) -> List[CalendarEvent]:
        today = date.today()
        tasks = await self.task_repo.get_by_date_range(start_date, end_date)

        events: List[CalendarEvent] = []
        for task in tasks:
            if task.due_date is None:
                continue

            dt = task.due_date
            task_date = dt.date() if isinstance(dt, datetime) else dt
            task_time = dt.time().strftime("%H:%M") if isinstance(dt, datetime) else None

            events.append(CalendarEvent(
                id=task.id,
                type="task",
                title=task.title,
                date=task_date,
                time=task_time,
                status=task.status,
                contact_name=task.contact.name if task.contact else None,
                is_overdue=task_date < today and task.status != "completed",
                metadata={"description": task.description} if task.description else {},
            ))

        for task in await self.task_repo.get_recurring():
            if task.due_date is None:
                continue
            dt = task.due_date
            base_date = dt.date() if isinstance(dt, datetime) else dt
            task_time = dt.time().strftime("%H:%M") if isinstance(dt, datetime) else None
            until = task.repeat_until.date() if task.repeat_until else None
            for task_date in _recurrence_dates(base_date, task.recurrence, start_date, end_date, until):
                if task_date == base_date:
                    continue
                events.append(CalendarEvent(
                    id=task.id,
                    type="task",
                    title=task.title,
                    date=task_date,
                    time=task_time,
                    status=task.status,
                    contact_name=task.contact.name if task.contact else None,
                    is_overdue=task_date < today and task.status != "completed",
                    metadata={"description": task.description} if task.description else {},
                ))

        for event in await self.event_repo.get_by_date_range(start_date, end_date):
            events.append(CalendarEvent(
                id=event.id,
                type="event",
                title=event.title,
                date=event.date,
                time=event.time,
                status="scheduled",
                contact_name=event.contact.name if event.contact else None,
                is_overdue=event.date < today,
                metadata={"description": event.description} if event.description else {},
            ))

        for event in await self.event_repo.get_recurring():
            for ev_date in _recurrence_dates(event.date, event.recurrence, start_date, end_date):
                if ev_date == event.date:
                    continue
                events.append(CalendarEvent(
                    id=event.id,
                    type="event",
                    title=event.title,
                    date=ev_date,
                    time=event.time,
                    status="scheduled",
                    contact_name=event.contact.name if event.contact else None,
                    is_overdue=ev_date < today,
                    metadata={"description": event.description} if event.description else {},
                ))

        events.extend(await self._birthday_events(start_date, end_date))

        events.sort(key=lambda e: (e.date, e.time or ""))
        return events

    async def _birthday_events(
        self, start_date: date, end_date: date
    ) -> List[CalendarEvent]:
        query = select(ContactModel).where(
            ContactModel.birthday.is_not(None),
            ContactModel.deleted_at.is_(None),
        )
        if self.owner_id is not None:
            query = query.where(ContactModel.owner_id == self.owner_id)
        contacts = (await self.session.execute(query)).scalars().all()

        events: List[CalendarEvent] = []
        for year in range(start_date.year, end_date.year + 1):
            for contact in contacts:
                birthday = contact.birthday
                if birthday is None:
                    continue
                try:
                    event_date = date(year, birthday.month, birthday.day)
                except ValueError:
                    continue
                if start_date <= event_date <= end_date:
                    events.append(CalendarEvent(
                        id=-int(contact.id),
                        type="birthday",
                        title=f"День рождения: {contact.name}",
                        date=event_date,
                        time=None,
                        status="scheduled",
                        contact_name=contact.name,
                        is_overdue=False,
                    ))
        return events

    @staticmethod
    def _to_response(event: CalendarEventModel) -> CalendarEventResponse:
        return CalendarEventResponse(
            id=event.id,
            contact_id=event.contact_id,
            contact_name=event.contact.name if event.contact else None,
            title=event.title,
            date=event.date,
            time=event.time,
            description=event.description,
            reminder_minutes=event.reminder_minutes,
            recurrence=event.recurrence,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    async def create_event(self, data: CalendarEventCreate) -> CalendarEventResponse:
        event = await self.event_repo.create(**data.model_dump())
        detail = await self.event_repo.get_detail(int(event.id))
        assert detail is not None
        return self._to_response(detail)

    async def get_event(self, event_id: int) -> Optional[CalendarEventResponse]:
        event = await self.event_repo.get_detail(event_id)
        return self._to_response(event) if event else None

    async def update_event(
        self, event_id: int, data: CalendarEventUpdate
    ) -> Optional[CalendarEventResponse]:
        event = await self.event_repo.update(
            event_id, **data.model_dump(exclude_unset=True)
        )
        if event is None:
            return None
        event = await self.event_repo.get_detail(event_id)
        return self._to_response(event) if event else None

    async def delete_event(self, event_id: int) -> bool:
        return await self.event_repo.delete(event_id)
