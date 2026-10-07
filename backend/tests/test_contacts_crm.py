import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _client():
    return make_client()


@pytest.mark.asyncio
async def test_notes_crud():
    async with await _client() as client:
        contact = (
            await client.post("/api/contacts/", json={"name": "Анна"})
        ).json()
        n = await client.post(
            f"/api/contacts/{contact['id']}/notes",
            json={"content": "Первая заметка", "author": "me"},
        )
        assert n.status_code == 201
        assert n.json()["content"] == "Первая заметка"

        notes = await client.get(f"/api/contacts/{contact['id']}/notes")
        assert len(notes.json()) == 1

        deleted = await client.delete(
            f"/api/contacts/notes/{n.json()['id']}"
        )
        assert deleted.status_code == 204
        notes = await client.get(f"/api/contacts/{contact['id']}/notes")
        assert notes.json() == []


@pytest.mark.asyncio
async def test_notes_empty_and_missing():
    async with await _client() as client:
        contact = (
            await client.post("/api/contacts/", json={"name": "Пусто"})
        ).json()
        notes = await client.get(f"/api/contacts/{contact['id']}/notes")
        assert notes.json() == []

        missing = await client.get("/api/contacts/999999/notes")
        assert missing.status_code == 404 or missing.status_code == 200


@pytest.mark.asyncio
async def test_timeline_empty_and_with_activity():
    async with await _client() as client:
        contact = (
            await client.post("/api/contacts/", json={"name": "Таймлайн"})
        ).json()
        timeline = await client.get(f"/api/contacts/{contact['id']}/timeline")
        assert timeline.status_code == 200
        assert timeline.json() == []

        await client.post(
            "/api/messages/",
            json={
                "contact_id": contact["id"],
                "channel": "telegram",
                "content": "сообщение",
                "direction": "incoming",
            },
        )
        timeline = (
            await client.get(f"/api/contacts/{contact['id']}/timeline")
        ).json()
        assert len(timeline) >= 1
        assert timeline[0]["type"] == "message"
        assert (
            "сообщение" in timeline[0]["title"]
            or "сообщение" in timeline[0]["subtitle"]
        )


@pytest.mark.asyncio
async def test_delete_note_missing_404():
    async with await _client() as client:
        r = await client.delete("/api/contacts/notes/999999")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_contacts_csv():
    async with await _client() as client:
        await client.post(
            "/api/contacts/",
            json={"name": "Экспорт", "email": "exp@x.ru"},
        )
        r = await client.get("/api/contacts/export")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]
        assert "Экспорт" in r.text
        assert "exp@x.ru" in r.text


@pytest.mark.asyncio
async def test_export_empty():
    async with await _client() as client:
        r = await client.get("/api/contacts/export")
        assert r.status_code == 200
        assert "name" in r.text


@pytest.mark.asyncio
async def test_import_contacts_csv():
    async with await _client() as client:
        csv = "name,phone,email\nНовый, +79170001122, new@x.ru\n"
        files = {"file": ("contacts.csv", csv, "text/csv")}
        r = await client.post("/api/contacts/import", files=files)
        assert r.status_code == 200
        data = r.json()
        assert data["created"] == 1
        assert data["updated"] == 0

        listing = await client.get("/api/contacts/")
        assert any(c["name"] == "Новый" for c in listing.json())


@pytest.mark.asyncio
async def test_import_bad_csv():
    async with await _client() as client:
        files = {"file": ("bad.csv", "name,phone\n", "text/csv")}
        r = await client.post("/api/contacts/import", files=files)
        assert r.status_code == 200
        assert r.json()["created"] == 0
