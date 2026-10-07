import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_contact(client, name: str = "Supplier Contact") -> int:
    response = await client.post("/api/contacts/", json={"name": name})
    return int(response.json()["id"])


@pytest.mark.asyncio
async def test_create_supplier():
    async with make_client() as client:
        cid = await _create_contact(client)

        response = await client.post("/api/suppliers/", json={
            "contact_id": cid,
            "company_name": "ООО Ромашка",
            "inn": "1234567890",
            "notes": "Поставщик мебели",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["contact_id"] == cid
    assert data["company_name"] == "ООО Ромашка"
    assert data["inn"] == "1234567890"
    assert data["contact_name"] is not None


@pytest.mark.asyncio
async def test_create_supplier_duplicate_contact_rejected():
    async with make_client() as client:
        cid = await _create_contact(client)
        await client.post("/api/suppliers/", json={"contact_id": cid})

        response = await client.post("/api/suppliers/", json={"contact_id": cid})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_supplier_nonexistent_contact_rejected():
    async with make_client() as client:
        response = await client.post("/api/suppliers/", json={"contact_id": 99999})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_suppliers():
    async with make_client() as client:
        cid = await _create_contact(client)
        await client.post("/api/suppliers/", json={"contact_id": cid})

        response = await client.get("/api/suppliers/")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_get_supplier_by_id():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/suppliers/", json={"contact_id": cid})
        sid = int(created.json()["id"])

        response = await client.get(f"/api/suppliers/{sid}")
    assert response.status_code == 200
    assert response.json()["id"] == sid


@pytest.mark.asyncio
async def test_update_supplier():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/suppliers/", json={"contact_id": cid})
        sid = int(created.json()["id"])

        response = await client.patch(f"/api/suppliers/{sid}", json={"company_name": "New LLC"})
    assert response.status_code == 200
    assert response.json()["company_name"] == "New LLC"


@pytest.mark.asyncio
async def test_delete_supplier():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/suppliers/", json={"contact_id": cid})
        sid = int(created.json()["id"])

        response = await client.delete(f"/api/suppliers/{sid}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_supplier_products():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/suppliers/", json={"contact_id": cid})
        sid = int(created.json()["id"])

        await client.post("/api/products/", json={
            "name": "Товар 1", "sku": "S-P1", "supplier_id": sid, "price": 100,
        })
        await client.post("/api/products/", json={
            "name": "Товар 2", "sku": "S-P2", "price": 200,
        })

        response = await client.get(f"/api/suppliers/{sid}/products")
    assert response.status_code == 200
    data = response.json()
    names = [p["name"] for p in data]
    assert "Товар 1" in names
    assert "Товар 2" not in names


@pytest.mark.asyncio
async def test_supplier_missing_contact_in_response():
    async with make_client() as client:
        cid = await _create_contact(client, "Иван Поставщиков")
        created = await client.post("/api/suppliers/", json={"contact_id": cid})

        response = await client.get(f"/api/suppliers/{int(created.json()['id'])}")
    assert response.status_code == 200
    assert response.json()["contact_name"] == "Иван Поставщиков"
