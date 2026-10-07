from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import AsyncSessionLocal, init_db
from app.repositories.task import TaskRepository
from app.services.reminder_scheduler import ReminderScheduler, ReminderService
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _seed_tasks(session) -> None:
    repo = TaskRepository(session)
    now = datetime.now()
    await repo.create(
        title="Due now",
        due_date=now - timedelta(minutes=5),
        reminder_minutes=10,
    )
    await repo.create(
        title="Future",
        due_date=now + timedelta(hours=1),
        reminder_minutes=10,
    )
    await repo.create(
        title="No reminder",
        due_date=now - timedelta(hours=1),
    )
    await repo.create(title="No due", reminder_minutes=10)


@pytest.mark.asyncio
async def test_fire_due_fires_only_due_reminders():
    async with AsyncSessionLocal() as session:
        await _seed_tasks(session)
        service = ReminderService(session)
        fired = await service.fire_due()
        await session.commit()
    assert fired == 1


@pytest.mark.asyncio
async def test_fire_due_does_not_duplicate():
    async with AsyncSessionLocal() as session:
        await _seed_tasks(session)
        service = ReminderService(session)
        first = await service.fire_due()
        await session.commit()
        second = await service.fire_due()
        await session.commit()
    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_fire_due_no_due_date_no_event():
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        await repo.create(title="No due date", reminder_minutes=10)
        await repo.create(title="No minutes", due_date=datetime.now())
        service = ReminderService(session)
        fired = await service.fire_due()
        await session.commit()
    assert fired == 0


@pytest.mark.asyncio
async def test_get_reminders_endpoint_returns_fired():
    async with make_client() as client:
        due = datetime.now() - timedelta(minutes=5)
        await client.post("/api/tasks/", json={
            "title": "Remind me",
            "due_date": due.strftime("%Y-%m-%dT%H:%M:%S"),
            "reminder_minutes": 10,
        })

    async with AsyncSessionLocal() as session:
        service = ReminderService(session)
        await service.fire_due()
        await session.commit()

    async with make_client() as client:
        resp = await client.get("/api/reminders/")
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Remind me" in titles


@pytest.mark.asyncio
async def test_get_reminders_empty_when_nothing_fired():
    async with make_client() as client:
        await client.post("/api/tasks/", json={"title": "Plain task"})

        resp = await client.get("/api/reminders/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_reminder_scheduler_start_stop():
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    factory = MagicMock(return_value=session)

    scheduler = ReminderScheduler(factory, interval=60)
    scheduler.start()
    assert scheduler._task is not None
    assert not scheduler._task.done()

    await scheduler.stop()
    assert scheduler._task is None
