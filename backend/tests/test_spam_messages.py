import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _make_contact(client, name: str, **extra) -> int:
    resp = await client.post("/api/contacts/", json={"name": name, **extra})
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _make_message(client, contact_id: int, content: str) -> None:
    resp = await client.post("/api/messages/", json={
        "contact_id": contact_id,
        "channel": "telegram",
        "content": content,
        "direction": "incoming",
        "status": "unread",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_spam_messages_hidden_from_inbox():
    async with make_client() as client:
        normal_id = await _make_contact(client, "Обычный")
        spam_id = await _make_contact(client, "Спамер")
        mark = await client.patch(f"/api/contacts/{spam_id}", json={"life_sphere": "spam"})
        assert mark.status_code == 200

        await _make_message(client, normal_id, "Привет, это нормальное сообщение")
        await _make_message(client, spam_id, "Купите слона")

        inbox = await client.get("/api/messages/inbox")
        all_msgs = await client.get("/api/messages/")

    inbox_contents = [m["content"] for m in inbox.json()]
    all_contents = [m["content"] for m in all_msgs.json()]
    assert "Купите слона" not in inbox_contents
    assert "Купите слона" not in all_contents
    assert "Привет, это нормальное сообщение" in inbox_contents


@pytest.mark.asyncio
async def test_spam_endpoint_returns_only_spam():
    async with make_client() as client:
        normal_id = await _make_contact(client, "Обычный")
        spam_id = await _make_contact(client, "Спамер")
        await client.patch(f"/api/contacts/{spam_id}", json={"life_sphere": "spam"})

        await _make_message(client, normal_id, "нормальное")
        await _make_message(client, spam_id, "спам-сообщение")

        response = await client.get("/api/messages/spam")
    assert response.status_code == 200
    contents = [m["content"] for m in response.json()]
    assert contents == ["спам-сообщение"]


@pytest.mark.asyncio
async def test_spam_count_counts_only_unread():
    async with make_client() as client:
        spam_id = await _make_contact(client, "Спамер")
        await client.patch(f"/api/contacts/{spam_id}", json={"life_sphere": "spam"})

        await _make_message(client, spam_id, "первый")
        read_resp = await client.post("/api/messages/", json={
            "contact_id": spam_id,
            "channel": "telegram",
            "content": "прочитанный",
            "direction": "incoming",
            "status": "read",
        })
        assert read_resp.status_code == 201

        response = await client.get("/api/messages/spam/count")
    assert response.status_code == 200
    assert response.json()["count"] == 1
