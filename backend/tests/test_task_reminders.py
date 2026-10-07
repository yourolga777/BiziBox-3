import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_reminder_minutes_stored():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/", json={"title": "Reminder task", "reminder_minutes": 15}
        )
    assert resp.status_code == 201
    assert resp.json()["reminder_minutes"] == 15


@pytest.mark.asyncio
async def test_reminder_at_equals_due_date_minus_minutes():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/",
            json={
                "title": "Timed reminder",
                "due_date": "2026-08-27T10:00:00",
                "reminder_minutes": 30,
            },
        )
    assert resp.status_code == 201
    assert resp.json()["reminder_at"] == "2026-08-27T09:30:00"


@pytest.mark.asyncio
async def test_reminder_at_in_detail():
    async with make_client() as client:
        created = await client.post(
            "/api/tasks/",
            json={
                "title": "Detail reminder",
                "due_date": "2026-08-27T10:00:00",
                "reminder_minutes": 30,
            },
        )
        tid = created.json()["id"]

        detail = await client.get(f"/api/tasks/{tid}")
    assert detail.status_code == 200
    assert detail.json()["reminder_at"] == "2026-08-27T09:30:00"


@pytest.mark.asyncio
async def test_reminder_without_due_date_ignored():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/", json={"title": "No due date", "reminder_minutes": 30}
        )
    assert resp.status_code == 201
    assert resp.json()["reminder_at"] is None


@pytest.mark.asyncio
async def test_reminder_without_minutes_ignored():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/", json={"title": "No minutes", "due_date": "2026-08-27T10:00:00"}
        )
    assert resp.status_code == 201
    assert resp.json()["reminder_at"] is None
