import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_task_crud_all_statuses():
    async with make_client() as client:
        for status in ("new", "in_progress", "completed", "cancelled"):
            resp = await client.post(
                "/api/tasks/", json={"title": f"Task {status}", "status": status}
            )
            assert resp.status_code == 201
            assert resp.json()["status"] == status

            tid = resp.json()["id"]
            detail = await client.get(f"/api/tasks/{tid}")
            assert detail.json()["status"] == status


@pytest.mark.asyncio
async def test_task_recurrence_valid_values():
    async with make_client() as client:
        for recurrence in ("daily", "weekly", "monthly"):
            resp = await client.post(
                "/api/tasks/",
                json={"title": f"Recurrence {recurrence}", "recurrence": recurrence},
            )
            assert resp.status_code == 201
            assert resp.json()["recurrence"] == recurrence


@pytest.mark.asyncio
async def test_task_recurrence_invalid_returns_422():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/", json={"title": "Bad recurrence", "recurrence": "yearly"}
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_task_reminder_minutes_ge_zero():
    async with make_client() as client:
        ok = await client.post(
            "/api/tasks/", json={"title": "Reminder", "reminder_minutes": 30}
        )
        assert ok.status_code == 201

        bad = await client.post(
            "/api/tasks/", json={"title": "Bad reminder", "reminder_minutes": -5}
        )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_completed_to_new_blocked_returns_400():
    async with make_client() as client:
        created = await client.post(
            "/api/tasks/", json={"title": "Done task", "status": "completed"}
        )
        tid = created.json()["id"]

        resp = await client.patch(f"/api/tasks/{tid}", json={"status": "new"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_completed_to_in_progress_allowed():
    async with make_client() as client:
        created = await client.post(
            "/api/tasks/", json={"title": "Done task", "status": "completed"}
        )
        tid = created.json()["id"]

        resp = await client.patch(
            f"/api/tasks/{tid}", json={"status": "in_progress"}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_new_to_completed_allowed():
    async with make_client() as client:
        created = await client.post("/api/tasks/", json={"title": "New task"})
        tid = created.json()["id"]

        resp = await client.patch(
            f"/api/tasks/{tid}", json={"status": "completed"}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_create_repeat_dates_materializes():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/",
            json={
                "title": "Repeat",
                "due_date": "2026-09-20T15:30:00",
                "repeat_dates": ["2026-09-25", "2026-09-30"],
            },
        )
        assert resp.status_code == 201

        all_tasks = (await client.get("/api/tasks/")).json()
        repeats = [t for t in all_tasks if t["title"] == "Repeat"]
        assert len(repeats) == 3  # дедлайн + 2 даты повтора
        for t in repeats:
            assert "15:30" in (t["due_date"] or "")


@pytest.mark.asyncio
async def test_create_recurrence_with_repeat_until():
    async with make_client() as client:
        resp = await client.post(
            "/api/tasks/",
            json={
                "title": "Daily",
                "due_date": "2026-09-20T09:00:00",
                "recurrence": "daily",
                "repeat_until": "2026-09-23T00:00:00",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["recurrence"] == "daily"
        assert body["repeat_until"] is not None


@pytest.mark.asyncio
async def test_detail_returns_repeat_fields():
    async with make_client() as client:
        created = await client.post(
            "/api/tasks/",
            json={
                "title": "Weekly",
                "due_date": "2026-09-20T09:00:00",
                "recurrence": "weekly",
                "repeat_until": "2026-10-20T00:00:00",
            },
        )
        tid = created.json()["id"]
        detail = (await client.get(f"/api/tasks/{tid}")).json()
        assert detail["recurrence"] == "weekly"
        assert detail["repeat_until"] is not None
