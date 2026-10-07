from datetime import datetime, timedelta

import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_get_events_returns_tasks_in_range():
    async with make_client() as client:
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        r1 = await client.post("/api/tasks/", json={"title": "Task today", "due_date": today})
        assert r1.status_code == 201
        r2 = await client.post("/api/tasks/", json={"title": "Task tomorrow", "due_date": tomorrow})
        assert r2.status_code == 201

        response = await client.get(f"/api/calendar/events?start={today}&end={tomorrow}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    titles = [e["title"] for e in data["events"]]
    assert "Task today" in titles
    assert "Task tomorrow" in titles


@pytest.mark.asyncio
async def test_get_events_empty_period():
    async with make_client() as client:
        response = await client.get("/api/calendar/events?start=2020-01-01&end=2020-01-31")
    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.asyncio
async def test_get_events_excludes_out_of_range():
    async with make_client() as client:
        await client.post("/api/tasks/", json={"title": "Far future", "due_date": "2030-12-01"})

        response = await client.get("/api/calendar/events?start=2020-01-01&end=2020-01-31")
    assert response.status_code == 200
    assert len(response.json()["events"]) == 0


@pytest.mark.asyncio
async def test_get_events_overdue_true():
    async with make_client() as client:
        past = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        await client.post("/api/tasks/", json={"title": "Overdue task", "due_date": past})

        today = datetime.now().strftime("%Y-%m-%d")
        response = await client.get(f"/api/calendar/events?start={past}&end={today}")
    assert response.status_code == 200
    events = response.json()["events"]
    overdue = [e for e in events if e["is_overdue"]]
    assert len(overdue) == 1
    assert overdue[0]["title"] == "Overdue task"


@pytest.mark.asyncio
async def test_get_events_overdue_false_for_completed():
    async with make_client() as client:
        past = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        r = await client.post("/api/tasks/", json={"title": "Completed old task", "due_date": past})
        task_id = r.json()["id"]
        await client.patch(f"/api/tasks/{task_id}", json={"status": "completed"})

        today = datetime.now().strftime("%Y-%m-%d")
        response = await client.get(f"/api/calendar/events?start={past}&end={today}")
    assert response.status_code == 200
    events = response.json()["events"]
    completed = [e for e in events if e["title"] == "Completed old task"]
    assert len(completed) == 1
    assert completed[0]["is_overdue"] is False


@pytest.mark.asyncio
async def test_get_events_without_due_date_ignored():
    async with make_client() as client:
        await client.post("/api/tasks/", json={"title": "No due date task"})

        response = await client.get("/api/calendar/events?start=2099-01-01&end=2099-01-31")
    assert response.status_code == 200
    assert len(response.json()["events"]) == 0


@pytest.mark.asyncio
async def test_get_events_with_contact_name():
    async with make_client() as client:
        contact = await client.post("/api/contacts/", json={"name": "Calendar Contact", "phone": "+77777777777"})
        cid = contact.json()["id"]
        await client.post(
            "/api/tasks/",
            json={"title": "Task with contact", "due_date": "2099-06-15", "contact_id": cid},
        )

        response = await client.get("/api/calendar/events?start=2099-01-01&end=2099-12-31")
    assert response.status_code == 200
    events = response.json()["events"]
    contact_events = [e for e in events if e["title"] == "Task with contact"]
    assert len(contact_events) == 1
    assert contact_events[0]["contact_name"] == "Calendar Contact"


@pytest.mark.asyncio
async def test_get_events_preserves_time():
    async with make_client() as client:
        today = datetime.now().strftime("%Y-%m-%d")
        await client.post(
            "/api/tasks/",
            json={"title": "Timed task", "due_date": f"{today}T14:30:00"},
        )

        response = await client.get(f"/api/calendar/events?start={today}&end={today}")
    assert response.status_code == 200
    events = response.json()["events"]
    timed = [e for e in events if e["title"] == "Timed task"]
    assert len(timed) == 1
    assert timed[0]["time"] == "14:30"


@pytest.mark.asyncio
async def test_get_events_date_only_defaults_to_midnight():
    async with make_client() as client:
        today = datetime.now().strftime("%Y-%m-%d")
        await client.post(
            "/api/tasks/",
            json={"title": "Date only task", "due_date": today},
        )

        response = await client.get(f"/api/calendar/events?start={today}&end={today}")
    assert response.status_code == 200
    events = response.json()["events"]
    date_only = [e for e in events if e["title"] == "Date only task"]
    assert len(date_only) == 1
    assert date_only[0]["time"] == "00:00"


@pytest.mark.asyncio
async def test_task_invalid_status_returns_422():
    async with make_client() as client:
        r = await client.post("/api/tasks/", json={"title": "Task", "status": "foo"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_recurrence_bounded_by_repeat_until():
    async with make_client() as client:
        await client.post(
            "/api/tasks/",
            json={
                "title": "Bounded daily",
                "due_date": "2026-09-01T10:00:00",
                "recurrence": "daily",
                "repeat_until": "2026-09-05T00:00:00",
            },
        )

        response = await client.get(
            "/api/calendar/events?start=2026-09-01&end=2026-09-30"
        )
    assert response.status_code == 200
    events = [e for e in response.json()["events"] if e["title"] == "Bounded daily"]
    dates = sorted(e["date"] for e in events)
    assert len(events) == 5  # 1..5 сентября
    assert max(dates) == "2026-09-05"
