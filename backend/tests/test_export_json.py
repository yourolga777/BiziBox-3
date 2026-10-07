import uuid

import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


_uid = uuid.uuid4().hex[:6]


@pytest.mark.asyncio
async def test_export_all_returns_valid_json():
    async with make_client() as client:
        response = await client.get("/api/export/all")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].startswith("attachment; filename=bizibox-export-")

    data = response.json()
    assert "meta" in data
    assert data["meta"]["app"] == "BiziBox"
    assert "exported_at" in data["meta"]

    for key in ("contacts", "messages", "tasks"):
        assert key in data, f"Missing key: {key}"
        assert isinstance(data[key], list)


@pytest.mark.asyncio
async def test_export_includes_seeded_data():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "Экспорт-контакт", "phone": "+70000000001"})

        response = await client.get("/api/export/all")
    data = response.json()

    contact_names = [c["name"] for c in data["contacts"]]
    assert "Экспорт-контакт" in contact_names
