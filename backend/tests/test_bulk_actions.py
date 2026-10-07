import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_messages(client, count):
    ids = []
    for i in range(count):
        contact = await client.post(
            "/api/contacts/", json={"name": f"Bulk {i}"}
        )
        cid = contact.json()["id"]
        created = await client.post(
            "/api/messages/",
            json={
                "contact_id": cid,
                "channel": "telegram",
                "content": f"message {i}",
                "direction": "incoming",
            },
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])
    return ids


@pytest.mark.asyncio
async def test_bulk_read():
    async with make_client() as client:
        ids = await _create_messages(client, 3)
        response = await client.post(
            "/api/messages/bulk/read", json={"ids": ids}
        )
    assert response.status_code == 200
    assert response.json()["read"] == 3


@pytest.mark.asyncio
async def test_bulk_read_marks_messages_read():
    async with make_client() as client:
        ids = await _create_messages(client, 2)
        await client.post("/api/messages/bulk/read", json={"ids": ids})
        detail = await client.get(f"/api/messages/{ids[0]}")
    assert detail.json()["status"] == "read"


@pytest.mark.asyncio
async def test_bulk_archive():
    async with make_client() as client:
        ids = await _create_messages(client, 2)
        response = await client.post(
            "/api/messages/bulk/archive", json={"ids": ids}
        )
        detail = await client.get(f"/api/messages/{ids[0]}")
    assert response.status_code == 200
    assert response.json()["archived"] == 2
    assert detail.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_bulk_delete():
    async with make_client() as client:
        ids = await _create_messages(client, 2)
        response = await client.post(
            "/api/messages/bulk/delete", json={"ids": ids}
        )
        listing = await client.get("/api/messages/")
    assert response.status_code == 200
    assert response.json()["deleted"] == 2
    listed_ids = [m["id"] for m in listing.json()]
    assert ids[0] not in listed_ids
    assert ids[1] not in listed_ids


@pytest.mark.asyncio
async def test_bulk_empty_ids_returns_400():
    async with make_client() as client:
        for path in ("read", "archive", "delete"):
            response = await client.post(
                f"/api/messages/bulk/{path}", json={"ids": []}
            )
            assert response.status_code == 400, path
