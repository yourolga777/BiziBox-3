from datetime import date, datetime, timedelta

import pytest

from app.repositories.calendar_event import CalendarEventRepository
from app.repositories.task import TaskRepository
from app.services.reminder_scheduler import ReminderService


@pytest.mark.asyncio
async def test_fire_due_marks_due_task_and_event_reminders(db_session):
    task_repo = TaskRepository(db_session)
    event_repo = CalendarEventRepository(db_session)

    now = datetime(2026, 9, 17, 12, 0, 0)

    task = await task_repo.create(
        title="Задача",
        due_date=now - timedelta(minutes=30),
        reminder_minutes=0,
    )
    event = await event_repo.create(
        title="Событие со временем",
        date=date(2026, 9, 17),
        time="09:00",
        reminder_minutes=60,
    )
    event_no_time = await event_repo.create(
        title="Событие без времени",
        date=date(2026, 9, 17),
        time=None,
        reminder_minutes=0,
    )
    await task_repo.create(
        title="Будущая",
        due_date=now + timedelta(days=1),
        reminder_minutes=30,
    )

    service = ReminderService(db_session)
    fired = await service.fire_due(now=now)
    assert fired == 3

    titles = {r["title"] for r in await service.get_fired()}
    assert titles == {"Задача", "Событие со временем", "Событие без времени"}
    assert "Будущая" not in titles

    assert int(task.id) in [r["id"] for r in await service.get_fired() if r["kind"] == "task"]
    assert int(event.id) in [r["id"] for r in await service.get_fired() if r["kind"] == "event"]
    assert int(event_no_time.id) in [r["id"] for r in await service.get_fired() if r["kind"] == "event"]


@pytest.mark.asyncio
async def test_fire_due_is_idempotent(db_session):
    task_repo = TaskRepository(db_session)
    now = datetime(2026, 9, 17, 12, 0, 0)

    await task_repo.create(
        title="Задача",
        due_date=now - timedelta(minutes=10),
        reminder_minutes=0,
    )

    service = ReminderService(db_session)
    assert await service.fire_due(now=now) == 1
    assert await service.fire_due(now=now) == 0


@pytest.mark.asyncio
async def test_ack_marks_seen(db_session):
    task_repo = TaskRepository(db_session)
    now = datetime(2026, 9, 17, 12, 0, 0)

    task = await task_repo.create(
        title="Обычная",
        due_date=now - timedelta(minutes=10),
        reminder_minutes=0,
    )
    service = ReminderService(db_session)
    await service.fire_due(now=now)
    assert len(await service.get_fired()) == 1

    assert await service.ack("task", int(task.id)) is True
    assert len(await service.get_fired()) == 0


@pytest.mark.asyncio
async def test_ack_advances_recurring_task(db_session):
    task_repo = TaskRepository(db_session)
    now = datetime(2026, 9, 17, 12, 0, 0)

    task = await task_repo.create(
        title="Ежедневная",
        due_date=now - timedelta(minutes=10),
        reminder_minutes=0,
        recurrence="daily",
    )
    orig_due = task.due_date
    service = ReminderService(db_session)
    await service.fire_due(now=now)

    assert await service.ack("task", int(task.id)) is True

    refreshed = await task_repo.get_by_id(int(task.id))
    assert refreshed is not None
    assert refreshed.due_date == orig_due + timedelta(days=1)
    assert refreshed.last_reminded_at is None
    assert refreshed.reminder_seen_at is None
    assert len(await service.get_fired()) == 0


@pytest.mark.asyncio
async def test_ack_advances_recurring_event(db_session):
    event_repo = CalendarEventRepository(db_session)
    now = datetime(2026, 9, 17, 12, 0, 0)

    event = await event_repo.create(
        title="Еженедельное",
        date=date(2026, 9, 17),
        time="09:00",
        reminder_minutes=60,
        recurrence="weekly",
    )
    orig_date = event.date
    service = ReminderService(db_session)
    await service.fire_due(now=now)

    assert await service.ack("event", int(event.id)) is True

    refreshed = await event_repo.get_by_id(int(event.id))
    assert refreshed is not None
    assert refreshed.date == orig_date + timedelta(days=7)
    assert refreshed.last_reminded_at is None
    assert refreshed.reminder_seen_at is None
