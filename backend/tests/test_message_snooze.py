from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.database import engine, init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_message(client):
    contact = await client.post("/api/contacts/", json={"name": "Snooze"})
    cid = contact.json()["id"]
    created = await client.post(
        "/api/messages/",
        json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "Напомни потом",
            "direction": "incoming",
        },
    )
    assert created.status_code == 201
    return created.json()["id"]


@pytest.mark.asyncio
async def test_message_snooze_future_roundtrip():
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        response = await client.patch(
            f"/api/messages/{mid}", json={"snoozed_until": future}
        )
    assert response.status_code == 200
    assert response.json()["snoozed_until"] is not None


@pytest.mark.asyncio
async def test_message_snooze_past_returns_422():
    past = (datetime.now() - timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        response = await client.patch(
            f"/api/messages/{mid}", json={"snoozed_until": past}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_message_snooze_clear_with_null():
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        await client.patch(f"/api/messages/{mid}", json={"snoozed_until": future})
        cleared = await client.patch(
            f"/api/messages/{mid}", json={"snoozed_until": None}
        )
    assert cleared.status_code == 200
    assert cleared.json()["snoozed_until"] is None


@pytest.mark.asyncio
async def test_message_create_snooze_past_returns_422():
    past = (datetime.now() - timedelta(hours=2)).isoformat()
    async with make_client() as client:
        contact = await client.post("/api/contacts/", json={"name": "Snooze Create"})
        cid = contact.json()["id"]
        response = await client.post(
            "/api/messages/",
            json={
                "contact_id": cid,
                "channel": "telegram",
                "content": "С прошлым snooze",
                "direction": "incoming",
                "snoozed_until": past,
            },
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_snooze_endpoint_accepts_until():
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        response = await client.patch(
            f"/api/messages/{mid}/snooze", json={"until": future}
        )
    assert response.status_code == 200
    assert response.json()["snoozed_until"] is not None


@pytest.mark.asyncio
async def test_snooze_endpoint_past_returns_422():
    past = (datetime.now() - timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        response = await client.patch(
            f"/api/messages/{mid}/snooze", json={"until": past}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_snoozed_message_hidden_from_new():
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    async with make_client() as client:
        snoozed_id = await _create_message(client)
        visible_id = await _create_message(client)
        await client.patch(
            f"/api/messages/{snoozed_id}/snooze", json={"until": future}
        )

        response = await client.get("/api/messages/", params={"scope": "new"})
    ids = [m["id"] for m in response.json()]
    assert snoozed_id not in ids
    assert visible_id in ids


@pytest.mark.asyncio
async def test_snoozed_message_visible_again_after_until():
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    async with make_client() as client:
        mid = await _create_message(client)
        await client.patch(f"/api/messages/{mid}/snooze", json={"until": future})

        hidden = await client.get("/api/messages/", params={"scope": "new"})
        assert mid not in [m["id"] for m in hidden.json()]

        past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE messages SET snoozed_until = :until WHERE id = :id"),
                {"until": past, "id": mid},
            )

        visible = await client.get("/api/messages/", params={"scope": "new"})
    assert mid in [m["id"] for m in visible.json()]
