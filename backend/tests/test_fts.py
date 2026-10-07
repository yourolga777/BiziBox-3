import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _make_contact(client, name: str) -> int:
    resp = await client.post("/api/contacts/", json={"name": name})
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _make_message(client, contact_id: int, content: str) -> dict:
    resp = await client.post(
        "/api/messages/",
        json={
            "contact_id": contact_id,
            "channel": "telegram",
            "content": content,
            "direction": "incoming",
            "status": "unread",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_search_returns_matching_messages():
    async with make_client() as client:
        cid = await _make_contact(client, "Иван")
        await _make_message(client, cid, "срочный заказ корабль доставка")
        await _make_message(client, cid, "обычное сообщение")

        resp = await client.get("/api/messages/search", params={"q": "корабль"})

    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert any("корабль" in c for c in contents)
    assert not any("обычное" in c for c in contents)


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty_list():
    async with make_client() as client:
        resp = await client.get("/api/messages/search", params={"q": ""})

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_flagged_filter_returns_only_flagged():
    async with make_client() as client:
        cid = await _make_contact(client, "Иван")
        flagged = await _make_message(client, cid, "флаговое сообщение")
        await _make_message(client, cid, "обычное сообщение")

        flag = await client.patch(f"/api/messages/{flagged['id']}", json={"is_flagged": True})
        assert flag.status_code == 200

        resp = await client.get("/api/messages/", params={"flagged": "true"})

    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "флаговое сообщение" in contents
    assert "обычное сообщение" not in contents
