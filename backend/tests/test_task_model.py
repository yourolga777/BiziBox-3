import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_task_status_sent_to_executor_returns_422():
    async with make_client() as client:
        r = await client.post(
            "/api/tasks/", json={"title": "Задача", "status": "sent_to_executor"}
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_reminder_and_recurrence_roundtrip():
    async with make_client() as client:
        created = await client.post(
            "/api/tasks/",
            json={
                "title": "Повторяющаяся задача",
                "reminder_minutes": 30,
                "recurrence": "daily",
            },
        )
    assert created.status_code == 201
    body = created.json()
    assert body["reminder_minutes"] == 30
    assert body["recurrence"] == "daily"


@pytest.mark.asyncio
async def test_task_negative_reminder_returns_422():
    async with make_client() as client:
        r = await client.post(
            "/api/tasks/", json={"title": "Задача", "reminder_minutes": -5}
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_response_has_no_removed_fields():
    async with make_client() as client:
        created = await client.post("/api/tasks/", json={"title": "Простая задача"})
    assert created.status_code == 201
    body = created.json()
    assert "executor_id" not in body
    assert body.get("message_id") is None
    assert "is_auto_generated" not in body


@pytest.mark.asyncio
async def test_task_detail_has_no_removed_fields():
    async with make_client() as client:
        created = await client.post("/api/tasks/", json={"title": "Детальная"})
        tid = created.json()["id"]
        detail = await client.get(f"/api/tasks/{tid}")
    assert detail.status_code == 200
    body = detail.json()
    assert "executor_id" not in body
    assert body.get("message_id") is None
    assert "is_auto_generated" not in body
    assert "message_content" not in body
