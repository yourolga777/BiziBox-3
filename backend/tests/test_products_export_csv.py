import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_contact(client, name: str = "Supplier") -> int:
    response = await client.post("/api/contacts/", json={"name": name})
    return int(response.json()["id"])


async def _seed_product(client, supplier_id: int | None = None, **kwargs) -> None:
    payload = {"name": "Товар", "sku": "SK-1", "price": 100, "purchase_price": 60, "stock": 10}
    if supplier_id is not None:
        payload["supplier_id"] = supplier_id
    payload.update(kwargs)
    response = await client.post("/api/products/", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_export_products_csv():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/suppliers/", json={"contact_id": cid})
        sid = int(created.json()["id"])
        await _seed_product(client, sid, name="Стул", sku="CH-1")

        response = await client.get("/api/products/export/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.text
    assert "name" in text
    assert "Стул" in text
    assert "CH-1" in text
    assert text.startswith("\ufeff") or "name" in text.splitlines()[0]


@pytest.mark.asyncio
async def test_export_products_csv_empty():
    async with make_client() as client:
        response = await client.get("/api/products/export/csv")
    assert response.status_code == 200
    assert "name" in response.text.splitlines()[0]
