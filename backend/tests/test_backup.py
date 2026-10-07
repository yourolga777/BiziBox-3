import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _seed(client):
    contact = await client.post(
        "/api/contacts/", json={"name": "Backup Contact", "phone": "+79990001122"}
    )
    cid = contact.json()["id"]
    msg = await client.post(
        "/api/messages/",
        json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "backup message",
            "direction": "incoming",
        },
    )
    task = await client.post("/api/tasks/", json={"title": "backup task"})
    return cid, msg.json()["id"], task.json()["id"]


@pytest.mark.asyncio
async def test_backup_export_is_encrypted():
    async with make_client() as client:
        await _seed(client)
        response = await client.post("/api/backup/export")
    assert response.status_code == 200
    body = response.text
    assert "Backup Contact" not in body
    assert "backup message" not in body
    assert body.startswith("gAAAA")


@pytest.mark.asyncio
async def test_backup_roundtrip_identical():
    async with make_client() as client:
        cid, mid, tid = await _seed(client)
        export = await client.post("/api/backup/export")
        token = export.text

        response = await client.post(
            "/api/backup/import",
            files={"file": ("backup.enc", token.encode(), "application/octet-stream")},
        )
        assert response.status_code == 200

        contact = await client.get(f"/api/contacts/{cid}")
        assert contact.json()["name"] == "Backup Contact"
        message = await client.get(f"/api/messages/{mid}")
        assert message.json()["content"] == "backup message"
        task = await client.get(f"/api/tasks/{tid}")
        assert task.json()["title"] == "backup task"


@pytest.mark.asyncio
async def test_backup_import_corrupt_returns_400():
    async with make_client() as client:
        response = await client.post(
            "/api/backup/import",
            files={"file": ("bad.enc", b"not-a-fernet-token", "application/octet-stream")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_backup_import_replaces_existing_data():
    async with make_client() as client:
        cid, _mid, _tid = await _seed(client)
        export = await client.post("/api/backup/export")
        token = export.text

        await client.delete(f"/api/contacts/{cid}")

        response = await client.post(
            "/api/backup/import",
            files={"file": ("backup.enc", token.encode(), "application/octet-stream")},
        )
        assert response.status_code == 200
        contact = await client.get(f"/api/contacts/{cid}")
        assert contact.json()["name"] == "Backup Contact"
