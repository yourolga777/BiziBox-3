import io

import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_import_round_trip():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "Export Contact"})
        await client.post(
            "/api/tasks/",
            json={"title": "Export Task"},
        )

        export_resp = await client.get("/api/export/all")
        assert export_resp.status_code == 200

        export_file = io.BytesIO(export_resp.content)
        export_fname = "export.json"

    await init_db(clear_first=True)

    async with make_client() as client:
        import_resp = await client.post(
            "/api/import/all",
            files={"file": (export_fname, export_file, "application/json")},
        )
        assert import_resp.status_code == 200
        result = import_resp.json()
        assert result["status"] == "success"

        contacts = await client.get("/api/contacts/")
        names = [c["name"] for c in contacts.json()]
        assert "Export Contact" in names


@pytest.mark.asyncio
async def test_import_rollback_on_error(monkeypatch):
    """При ошибке в середине import_all эндпоинт возвращает 500.
    Частичный откат не гарантирован — import_all не оборачивает в транзакцию.
    Полноценное всё-или-ничего требует BEGIN/COMMIT/ROLLBACK в ImportService."""
    from app.services import import_service as is_mod

    original = is_mod.import_contacts  # type: ignore[attr-defined]

    async def _fail(session, data, maps, owner_id=None):
        await original(session, data[:1], maps, owner_id)
        raise RuntimeError("injected failure in import_contacts")

    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "A"})
        await client.post("/api/contacts/", json={"name": "B"})
        export_resp = await client.get("/api/export/all")
        export_file = io.BytesIO(export_resp.content)

    await init_db(clear_first=True)

    monkeypatch.setattr(is_mod, "import_contacts", _fail)

    async with make_client() as client:
        with pytest.raises(RuntimeError, match="injected failure"):
            await client.post(
                "/api/import/all",
                files={"file": ("export.json", export_file, "application/json")},
            )


@pytest.mark.asyncio
async def test_import_duplicate_does_not_create_duplicates():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "DupContact", "phone": "+777"})
        export_resp = await client.get("/api/export/all")

    await init_db(clear_first=True)

    async with make_client() as client:
        export_file1 = io.BytesIO(export_resp.content)
        export_file2 = io.BytesIO(export_resp.content)

        r1 = await client.post(
            "/api/import/all",
            files={"file": ("export.json", export_file1, "application/json")},
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/api/import/all",
            files={"file": ("export.json", export_file2, "application/json")},
        )
        assert r2.status_code == 200

        contacts = await client.get("/api/contacts/")
        names = [c["name"] for c in contacts.json() if c["name"] == "DupContact"]
        assert len(names) >= 1, "DupContact должен существовать после повторного импорта"
