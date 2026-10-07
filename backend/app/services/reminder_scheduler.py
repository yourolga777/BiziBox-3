import asyncio
import logging
from datetime import datetime, timedelta
from datetime import time as dtime
from typing import Any, Callable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CalendarEventModel
from ..repositories.calendar_event import CalendarEventRepository
from ..repositories.task import TaskRepository

logger = logging.getLogger(__name__)


def _advance(value: Any, recurrence: str) -> Any:
    """Сдвигает date/datetime на шаг повторяемости (daily/weekly/monthly)."""
    if recurrence == "daily":
        return value + timedelta(days=1)
    if recurrence == "weekly":
        return value + timedelta(days=7)
    if recurrence == "monthly":
        import calendar as _cal

        month = value.month + 1
        year = value.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        last_day = _cal.monthrange(year, month)[1]
        return value.replace(year=year, month=month, day=min(value.day, last_day))
    return value


class ReminderService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.task_repo = TaskRepository(session, owner_id)
        self.event_repo = CalendarEventRepository(session, owner_id)

    @staticmethod
    def _event_reminder_at(event: CalendarEventModel) -> Optional[datetime]:
        if event.reminder_minutes is None or event.date is None:
            return None
        t = event.time or "00:00"
        try:
            hh, mm = str(t).split(":")
            event_dt = datetime.combine(event.date, dtime(int(hh), int(mm)))
        except (ValueError, TypeError):
            event_dt = datetime.combine(event.date, dtime(0, 0))
        return event_dt - timedelta(minutes=event.reminder_minutes)

    async def fire_due(self, now: Optional[datetime] = None) -> int:
        """Помечает напоминания задач и событий, чей reminder_at наступил.

        Возвращает число сработавших напоминаний. Повторный вызов не
        дублирует уже отправленные (last_reminded_at уже проставлен).
        """
        if now is None:
            now = datetime.now()

        task_candidates = await self.task_repo.get_reminder_candidates()
        task_ids = [
            int(t.id)
            for t in task_candidates
            if t.reminder_at is not None and t.reminder_at <= now
        ]
        if task_ids:
            await self.task_repo.mark_reminded(task_ids, now)

        event_candidates = await self.event_repo.get_reminder_candidates()
        event_ids = [
            int(e.id)
            for e in event_candidates
            if (ra := self._event_reminder_at(e)) is not None and ra <= now
        ]
        if event_ids:
            await self.event_repo.mark_reminded(event_ids, now)

        return len(task_ids) + len(event_ids)

    async def get_fired(self, limit: int = 50) -> List[dict[str, Any]]:
        tasks = await self.task_repo.get_fired_reminders(limit=limit)
        events = await self.event_repo.get_fired_reminders(limit=limit)

        reminders: List[dict[str, Any]] = []
        for t in tasks:
            reminders.append(
                {
                    "kind": "task",
                    "id": int(t.id),
                    "title": t.title,
                    "fired_at": t.last_reminded_at,
                    "recurrence": t.recurrence,
                    "when": t.due_date,
                }
            )
        for e in events:
            when = None
            if e.date is not None:
                time_str = e.time or "00:00"
                try:
                    hh, mm = str(time_str).split(":")
                    when = datetime.combine(e.date, dtime(int(hh), int(mm)))
                except (ValueError, TypeError):
                    when = datetime.combine(e.date, dtime(0, 0))
            reminders.append(
                {
                    "kind": "event",
                    "id": int(e.id),
                    "title": e.title,
                    "fired_at": e.last_reminded_at,
                    "recurrence": e.recurrence,
                    "when": when,
                }
            )

        reminders.sort(
            key=lambda r: r["fired_at"] or datetime.min, reverse=True
        )
        return reminders[:limit]

    async def ack(self, kind: str, reminder_id: int) -> bool:
        """Помечает напоминание просмотренным; повторяющееся — сдвигает вперёд."""
        if kind == "task":
            task = await self.task_repo.get_by_id(reminder_id)
            if task is None:
                return False
            if task.recurrence in ("daily", "weekly", "monthly") and task.due_date:
                await self.task_repo.update(
                    reminder_id,
                    due_date=_advance(task.due_date, task.recurrence),
                    last_reminded_at=None,
                    reminder_seen_at=None,
                )
            else:
                await self.task_repo.mark_reminder_seen(reminder_id)
            return True

        if kind == "event":
            event = await self.event_repo.get_by_id(reminder_id)
            if event is None:
                return False
            if event.recurrence in ("daily", "weekly", "monthly") and event.date:
                await self.event_repo.update(
                    reminder_id,
                    date=_advance(event.date, event.recurrence),
                    last_reminded_at=None,
                    reminder_seen_at=None,
                )
            else:
                await self.event_repo.mark_reminder_seen(reminder_id)
            return True

        return False


class ReminderScheduler:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        interval: int = 60,
    ):
        self.session_factory = session_factory
        self.interval = interval
        self._task: Optional[asyncio.Task[None]] = None

    async def _run(self) -> None:
        while True:
            try:
                async with self.session_factory() as session:
                    service = ReminderService(session)
                    fired = await service.fire_due()
                    await session.commit()
                    if fired:
                        logger.info("Fired %d reminder(s)", fired)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Reminder scheduler error: %s", e)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            logger.warning("Reminder scheduler already running")
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        task = self._task
        self._task = None
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
