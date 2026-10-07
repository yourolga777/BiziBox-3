import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_contact(client, name: str = "Supplier Inc") -> int:
    response = await client.post("/api/contacts/", json={"name": name})
    return int(response.json()["id"])


async def _create_supplier(client, contact_id: int) -> int:
    response = await client.post("/api/suppliers/", json={
        "contact_id": contact_id,
        "company_name": "Supplier LLC",
    })
    assert response.status_code == 201
    return int(response.json()["id"])


async def _create_product(client, supplier_id: int | None = None, **kwargs) -> int:
    payload = {
        "name": "Test Product",
        "sku": "TST-001",
        "price": 1000,
        "purchase_price": 700,
        "stock": 50,
        "unit": "шт",
    }
    if supplier_id is not None:
        payload["supplier_id"] = supplier_id
    payload.update(kwargs)
    response = await client.post("/api/products/", json=payload)
    assert response.status_code == 201
    return int(response.json()["id"])


@pytest.mark.asyncio
async def test_create_product():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)

        response = await client.post("/api/products/", json={
            "name": "Стул офисный",
            "sku": "CH-001",
            "price": 4500,
            "purchase_price": 3000,
            "stock": 20,
            "unit": "шт",
            "description": "Удобный стул",
            "supplier_id": sid,
        })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Стул офисный"
    assert data["sku"] == "CH-001"
    assert data["price"] == 4500
    assert data["purchase_price"] == 3000
    assert data["stock"] == 20
    assert data["unit"] == "шт"
    assert data["supplier_id"] == sid
    assert data["margin"] == 1500.0
    assert data["margin_percent"] == 50.0
    assert data["supplier_name"] is not None


@pytest.mark.asyncio
async def test_create_product_duplicate_sku_rejected():
    async with make_client() as client:
        await client.post("/api/products/", json={
            "name": "First", "sku": "SKU-UNIQ", "price": 100,
        })

        response = await client.post("/api/products/", json={
            "name": "Second", "sku": "SKU-UNIQ", "price": 200,
        })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_product_without_name_rejected():
    async with make_client() as client:
        response = await client.post("/api/products/", json={"sku": "NONAME"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_products():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        await _create_product(client, sid, name="P1", sku="SKU-1")
        await _create_product(client, sid, name="P2", sku="SKU-2")

        response = await client.get("/api/products/")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_get_product_by_id():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        pid = await _create_product(client, sid)

        response = await client.get(f"/api/products/{pid}")
    assert response.status_code == 200
    assert response.json()["id"] == pid


@pytest.mark.asyncio
async def test_get_product_404():
    async with make_client() as client:
        response = await client.get("/api/products/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_supplier():
    async with make_client() as client:
        cid1 = await _create_contact(client, "Supplier A")
        sid1 = await _create_supplier(client, cid1)
        cid2 = await _create_contact(client, "Supplier B")
        sid2 = await _create_supplier(client, cid2)

        await _create_product(client, sid1, name="A1", sku="A-1")
        await _create_product(client, sid2, name="B1", sku="B-1")

        response = await client.get(f"/api/products/?supplier_id={sid1}")
    assert response.status_code == 200
    data = response.json()
    names = [p["name"] for p in data]
    assert "A1" in names
    assert "B1" not in names


@pytest.mark.asyncio
async def test_search_products():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        await _create_product(client, sid, name="Alpha", sku="AL-1")
        await _create_product(client, sid, name="Beta", sku="BT-2")

        response = await client.get("/api/products/?search=Al")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alpha"


@pytest.mark.asyncio
async def test_update_product():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        pid = await _create_product(client, sid)

        response = await client.patch(f"/api/products/{pid}", json={
            "name": "Updated Name", "price": 9999,
        })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["price"] == 9999


@pytest.mark.asyncio
async def test_update_product_sku_conflict():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        await _create_product(client, sid, name="P1", sku="SK-X")
        pid2 = await _create_product(client, sid, name="P2", sku="SK-Y")

        response = await client.patch(f"/api/products/{pid2}", json={"sku": "SK-X"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_soft_delete_product():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        pid = await _create_product(client, sid)

        response = await client.delete(f"/api/products/{pid}")
    assert response.status_code == 204

    async with make_client() as client:
        response = await client.get("/api/products/")
        assert response.status_code == 200
        data = response.json()
        ids = [p["id"] for p in data]
        assert pid not in ids


@pytest.mark.asyncio
async def test_restore_product():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        pid = await _create_product(client, sid)

        await client.delete(f"/api/products/{pid}")
        response = await client.post(f"/api/products/{pid}/restore")
    assert response.status_code == 200
    assert response.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_delete_product_404():
    async with make_client() as client:
        response = await client.delete("/api/products/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suggest_products():
    async with make_client() as client:
        cid = await _create_contact(client)
        sid = await _create_supplier(client, cid)
        await _create_product(client, sid, name="Apple", sku="AP-1")

        response = await client.get('/api/products/suggest?q=App')
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Apple"


@pytest.mark.asyncio
async def test_margin_computes_zero_purchase_price():
    async with make_client() as client:
        response = await client.post("/api/products/", json={
            "name": "Freebie", "sku": "FREE", "price": 100, "purchase_price": 0,
        })
    assert response.status_code == 201
    data = response.json()
    assert data["margin"] == 100.0
    assert data["margin_percent"] is None


@pytest.mark.asyncio
async def test_product_without_supplier():
    async with make_client() as client:
        response = await client.post("/api/products/", json={
            "name": "Solo", "sku": "S-1", "price": 500,
        })
    assert response.status_code == 201
    data = response.json()
    assert data["supplier_id"] is None
    assert data["supplier_name"] is None
