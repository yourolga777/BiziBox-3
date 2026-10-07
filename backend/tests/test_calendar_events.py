import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_calendar_event_crud():
    async with make_client() as client:
        created = await client.post("/api/calendar/events", json={
            "title": "Meeting",
            "date": "2099-06-15",
            "time": "10:00",
            "recurrence": "weekly",
        })
        assert created.status_code == 201
        eid = created.json()["id"]
        assert created.json()["recurrence"] == "weekly"

        got = await client.get(f"/api/calendar/events/{eid}")
        assert got.status_code == 200
        assert got.json()["title"] == "Meeting"

        updated = await client.patch(
            f"/api/calendar/events/{eid}", json={"title": "Meeting+"}
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == "Meeting+"

        deleted = await client.delete(f"/api/calendar/events/{eid}")
        assert deleted.status_code == 204

        gone = await client.get(f"/api/calendar/events/{eid}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_calendar_events_merged_tasks_and_events():
    async with make_client() as client:
        day = "2099-06-15"
        await client.post(
            "/api/tasks/", json={"title": "Task merged", "due_date": day}
        )
        await client.post(
            "/api/calendar/events", json={"title": "Event merged", "date": day}
        )

        resp = await client.get(f"/api/calendar/events?start={day}&end={day}")
    assert resp.status_code == 200
    events = resp.json()["events"]
    types = {e["type"] for e in events}
    assert "task" in types
    assert "event" in types
    titles = {e["title"] for e in events}
    assert "Task merged" in titles
    assert "Event merged" in titles


@pytest.mark.asyncio
async def test_calendar_event_invalid_recurrence_422():
    async with make_client() as client:
        resp = await client.post("/api/calendar/events", json={
            "title": "Bad recurrence",
            "date": "2099-06-15",
            "recurrence": "yearly",
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_nonexistent_event_404():
    async with make_client() as client:
        resp = await client.delete("/api/calendar/events/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_calendar_event_with_contact_name():
    async with make_client() as client:
        contact = await client.post(
            "/api/contacts/", json={"name": "Event Contact"}
        )
        cid = contact.json()["id"]

        created = await client.post("/api/calendar/events", json={
            "title": "Linked event",
            "date": "2099-06-15",
            "contact_id": cid,
        })
    assert created.status_code == 201
    assert created.json()["contact_name"] == "Event Contact"


@pytest.mark.asyncio
async def test_calendar_event_invalid_time_422():
    async with make_client() as client:
        resp = await client.post("/api/calendar/events", json={
            "title": "Bad time",
            "date": "2099-06-15",
            "time": "25:99",
        })
    assert resp.status_code == 422
