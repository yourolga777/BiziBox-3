import json
import uuid

import pytest

from app.database import init_db
from tests.conftest import make_client

_uid = uuid.uuid4().hex[:6]


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


def _make_export(contacts=None, messages=None, tasks=None):
    return {
        "meta": {"exported_at": "2026-07-15T00:00:00", "version": "0.1.0", "app": "BiziBox"},
        "contacts": contacts or [],
        "messages": messages or [],
        "tasks": tasks or [],
    }


@pytest.mark.asyncio
async def test_import_all_creates_records():
    async with make_client() as client:
        data = _make_export(
            contacts=[{"id": 1, "name": "Импорт-контакт", "phone": f"+7111111111{_uid[:3]}"}],
        )
        content = json.dumps(data, ensure_ascii=False)
        response = await client.post(
            "/api/import/all",
            files={"file": ("test.json", content, "application/json")},
        )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["imported"]["contacts"]["created"] == 1


@pytest.mark.asyncio
async def test_import_updates_existing_by_unique_field():
    async with make_client() as client:
        await client.post(
            "/api/contacts/",
            json={"name": "Старое имя", "phone": f"+7222222222{_uid[:2]}", "telegram_id": f"tg_import_{_uid}"},
        )

        data = _make_export(
            contacts=[
                {"id": 999, "name": "Новое имя", "phone": f"+7222222222{_uid[:2]}", "telegram_id": f"tg_import_{_uid}"},
            ],
        )
        content = json.dumps(data, ensure_ascii=False)
        response = await client.post(
            "/api/import/all",
            files={"file": ("test.json", content, "application/json")},
        )
    assert response.status_code == 200
    result = response.json()
    assert result["imported"]["contacts"]["updated"] == 1
    assert result["imported"]["contacts"]["created"] == 0


@pytest.mark.asyncio
async def test_import_rejects_invalid_json():
    async with make_client() as client:
        response = await client.post(
            "/api/import/all",
            files={"file": ("bad.json", "not json", "application/json")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_rejects_missing_keys():
    async with make_client() as client:
        data: dict[str, object] = {"meta": {}, "contacts": []}
        content = json.dumps(data)
        response = await client.post(
            "/api/import/all",
            files={"file": ("test.json", content, "application/json")},
        )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "messages" in detail


@pytest.mark.asyncio
async def test_import_full_cycle():
    async with make_client() as client:
        await client.post(
            "/api/contacts/",
            json={"name": "Цикл-контакт", "phone": f"+7333333333{_uid[:2]}", "telegram_id": f"tg_cycle_{_uid}"},
        )

        export_resp = await client.get("/api/export/all")
        export_data = export_resp.json()

        await client.post("/api/contacts/", json={"name": "Доп-контакт", "phone": "+74444444444"})

        import_content = json.dumps(export_data, ensure_ascii=False)
        response = await client.post(
            "/api/import/all",
            files={"file": ("cycle.json", import_content, "application/json")},
        )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["imported"]["contacts"]["updated"] >= 1
    assert result["imported"]["contacts"]["created"] >= 0
