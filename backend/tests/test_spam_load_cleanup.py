from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import AsyncSessionLocal, init_db
from app.deps import set_poll_service
from app.services.message_service import MessageService
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_spam_load_returns_spam_messages():
    async with make_client() as client:
        spam = await client.post("/api/contacts/", json={
            "name": "Spammer", "life_sphere": "spam", "telegram_id": "spam_tg_1",
        })
        assert spam.status_code == 201

        adapter = AsyncMock()
        adapter.get_dialog.return_value = [
            {"message_id": "m1", "direction": "incoming", "content": "spam 1"},
            {"message_id": "m2", "direction": "incoming", "content": "spam 2"},
        ]
        ps = MagicMock()
        ps.get_channel.return_value = adapter
        set_poll_service(ps)

        resp = await client.post("/api/messages/spam/load")

    set_poll_service(None)
    assert resp.status_code == 200
    data = resp.json()
    assert data["loaded"] == 2
    assert [m["content"] for m in data["messages"]] == ["spam 1", "spam 2"]


@pytest.mark.asyncio
async def test_spam_load_skips_contacts_without_channel_id():
    async with make_client() as client:
        await client.post("/api/contacts/", json={
            "name": "Spammer no tg", "life_sphere": "spam",
        })

        ps = MagicMock()
        adapter = AsyncMock()
        ps.get_channel.return_value = adapter
        set_poll_service(ps)

        resp = await client.post("/api/messages/spam/load")

    set_poll_service(None)
    assert resp.status_code == 200
    assert resp.json()["loaded"] == 0
    adapter.get_dialog.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_spam_deletes_only_spam():
    async with make_client() as client:
        spam = await client.post(
            "/api/contacts/", json={"name": "Spammer", "life_sphere": "spam"}
        )
        spam_id = spam.json()["id"]
        normal = await client.post(
            "/api/contacts/", json={"name": "Normal"}
        )
        normal_id = normal.json()["id"]

        await client.post("/api/messages/", json={
            "contact_id": spam_id,
            "channel": "telegram",
            "content": "spam msg",
            "direction": "incoming",
        })
        await client.post("/api/messages/", json={
            "contact_id": normal_id,
            "channel": "telegram",
            "content": "normal msg",
            "direction": "incoming",
        })

    async with AsyncSessionLocal() as session:
        service = MessageService(session)
        deleted = await service.cleanup_spam()
        await session.commit()

    assert deleted == 1

    async with AsyncSessionLocal() as session:
        service = MessageService(session)
        remaining = await service.get_all()
    contents = [m.content for m in remaining]
    assert "normal msg" in contents
    assert "spam msg" not in contents


@pytest.mark.asyncio
async def test_cleanup_spam_handles_sphere_spam():
    async with make_client() as client:
        spam = await client.post(
            "/api/contacts/",
            json={"name": "Type Spam", "life_sphere": "spam"},
        )
        spam_id = spam.json()["id"]

        await client.post("/api/messages/", json={
            "contact_id": spam_id,
            "channel": "telegram",
            "content": "type spam msg",
            "direction": "incoming",
        })

    async with AsyncSessionLocal() as session:
        service = MessageService(session)
        deleted = await service.cleanup_spam()
        await session.commit()

    assert deleted == 1
