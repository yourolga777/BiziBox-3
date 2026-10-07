import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_birthday_event_generated():
    async with make_client() as client:
        await client.post("/api/contacts/", json={
            "name": "Анна",
            "birthday": "1990-06-15",
        })

        resp = await client.get(
            "/api/calendar/events?start=2099-06-01&end=2099-06-30"
        )
    assert resp.status_code == 200
    events = resp.json()["events"]
    birthdays = [e for e in events if e["type"] == "birthday"]
    assert len(birthdays) == 1
    assert birthdays[0]["title"] == "День рождения: Анна"
    assert birthdays[0]["date"] == "2099-06-15"


@pytest.mark.asyncio
async def test_contact_without_birthday_no_event():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "Без ДР"})

        resp = await client.get(
            "/api/calendar/events?start=2099-06-01&end=2099-06-30"
        )
    events = resp.json()["events"]
    assert all(e["type"] != "birthday" for e in events)


@pytest.mark.asyncio
async def test_birthday_repeats_each_year():
    async with make_client() as client:
        await client.post("/api/contacts/", json={
            "name": "Анна",
            "birthday": "1990-06-15",
        })

        resp = await client.get(
            "/api/calendar/events?start=2099-01-01&end=2100-12-31"
        )
    events = resp.json()["events"]
    dates = sorted(e["date"] for e in events if e["type"] == "birthday")
    assert dates == ["2099-06-15", "2100-06-15"]


@pytest.mark.asyncio
async def test_birthday_out_of_range_not_generated():
    async with make_client() as client:
        await client.post("/api/contacts/", json={
            "name": "Анна",
            "birthday": "1990-06-15",
        })

        resp = await client.get(
            "/api/calendar/events?start=2099-01-01&end=2099-01-31"
        )
    events = resp.json()["events"]
    assert all(e["type"] != "birthday" for e in events)


@pytest.mark.asyncio
async def test_leap_day_birthday_skipped_in_non_leap_year():
    async with make_client() as client:
        await client.post("/api/contacts/", json={
            "name": "Лев",
            "birthday": "2000-02-29",
        })

        resp = await client.get(
            "/api/calendar/events?start=2099-02-01&end=2099-03-31"
        )
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert all(e["type"] != "birthday" for e in events)
