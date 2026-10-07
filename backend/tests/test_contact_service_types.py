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


@pytest.mark.asyncio
async def test_contact_crud_supports_all_spheres():
    async with make_client() as client:
        for sphere in ("personal", "work", "spam"):
            resp = await client.post(
                "/api/contacts/",
                json={"name": f"Sphere {sphere}", "life_sphere": sphere},
            )
            assert resp.status_code == 201
            assert resp.json()["life_sphere"] == sphere

            cid = resp.json()["id"]
            detail = await client.get(f"/api/contacts/{cid}")
            assert detail.json()["life_sphere"] == sphere


@pytest.mark.asyncio
async def test_contact_sphere_defaults_to_null():
    async with make_client() as client:
        resp = await client.post("/api/contacts/", json={"name": "Без сферы"})
    assert resp.status_code == 201
    assert resp.json()["life_sphere"] is None


@pytest.mark.asyncio
async def test_contact_sphere_invalid_rejected_422():
    async with make_client() as client:
        created = await client.post(
            "/api/contacts/", json={"name": "Employee", "life_sphere": "employee"}
        )
    assert created.status_code == 422


@pytest.mark.asyncio
async def test_contact_create_with_nonexistent_folder_returns_400():
    async with make_client() as client:
        resp = await client.post(
            "/api/contacts/", json={"name": "Bad Folder", "folder_id": 999999}
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_contact_update_with_nonexistent_folder_returns_400():
    async with make_client() as client:
        cid = await _make_contact(client, "Contact")
        resp = await client.patch(
            f"/api/contacts/{cid}", json={"folder_id": 999999}
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_contact_update_with_existing_folder_succeeds():
    async with make_client() as client:
        folder = await client.post("/api/folders/", json={"name": "VIP"})
        fid = folder.json()["id"]
        cid = await _make_contact(client, "Contact")

        resp = await client.patch(f"/api/contacts/{cid}", json={"folder_id": fid})
    assert resp.status_code == 200
    assert resp.json()["folder_id"] == fid


@pytest.mark.asyncio
async def test_bulk_update_sphere():
    async with make_client() as client:
        cid = await _make_contact(client, "Contact")
        resp = await client.patch(
            "/api/contacts/bulk-update",
            json={"ids": [cid], "life_sphere": "work"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 1

        detail = await client.get(f"/api/contacts/{cid}")
    assert detail.json()["life_sphere"] == "work"


@pytest.mark.asyncio
async def test_contact_type_templates_crud():
    async with make_client() as client:
        created = await client.post(
            "/api/contacts/contact-types",
            json={"name": "Клиент", "sphere": "work"},
        )
        assert created.status_code == 201
        tid = created.json()["id"]
        assert created.json()["name"] == "Клиент"
        assert created.json()["sphere"] == "work"

        detail = await client.get("/api/contacts/contact-types")
        assert detail.status_code == 200
        assert any(t["id"] == tid for t in detail.json())

        patched = await client.patch(
            f"/api/contacts/contact-types/{tid}", json={"name": "Большой клиент"}
        )
        assert patched.status_code == 200
        assert patched.json()["name"] == "Большой клиент"

        deleted = await client.delete(f"/api/contacts/contact-types/{tid}")
        assert deleted.status_code == 204

        detail_after = await client.get("/api/contacts/contact-types")
        assert all(t["id"] != tid for t in detail_after.json())


@pytest.mark.asyncio
async def test_assign_contact_types():
    async with make_client() as client:
        tpl = await client.post(
            "/api/contacts/contact-types",
            json={"name": "Партнёр", "sphere": "work"},
        )
        tid = tpl.json()["id"]
        cid = await _make_contact(client, "Contact", contact_type_ids=[tid])

        detail = await client.get(f"/api/contacts/{cid}")
        assert tid in detail.json()["contact_type_ids"]
        assert "Партнёр" in detail.json()["contact_types"]


@pytest.mark.asyncio
async def test_delete_type_template_removes_associations():
    async with make_client() as client:
        tpl = await client.post(
            "/api/contacts/contact-types",
            json={"name": "Временный", "sphere": "personal"},
        )
        tid = tpl.json()["id"]
        cid = await _make_contact(client, "Contact", contact_type_ids=[tid])

        deleted = await client.delete(f"/api/contacts/contact-types/{tid}")
        assert deleted.status_code == 204

        detail = await client.get(f"/api/contacts/{cid}")
        assert detail.json()["contact_type_ids"] == []
        assert detail.json()["contact_types"] == []
