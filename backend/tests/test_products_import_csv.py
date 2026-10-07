import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


def _csv(text: str) -> bytes:
    return text.encode("utf-8")


async def _post_import(client, text: str):
    return await client.post(
        "/api/products/import",
        files={"file": ("products.csv", _csv(text), "text/csv")},
    )


@pytest.mark.asyncio
async def test_import_creates_products():
    async with make_client() as client:
        csv_text = (
            "name,sku,price,purchase_price,stock,unit,description,supplier\n"
            "Стол,ST-1,8000,5000,10,шт,Обеденный стол,\n"
            "Стул,CH-1,4500,3000,20,шт,,\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2
    assert data["skipped"] == 0

    async with make_client() as client:
        response = await client.get("/api/products/")
        names = {p["name"] for p in response.json()}
        assert {"Стол", "Стул"} <= names


@pytest.mark.asyncio
async def test_import_upserts_by_sku():
    async with make_client() as client:
        await client.post("/api/products/", json={
            "name": "Стол", "sku": "ST-1", "price": 7000,
        })

        csv_text = (
            "name,sku,price,purchase_price,stock,unit,description,supplier\n"
            "Стол обновлённый,ST-1,9000,6000,5,шт,,\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 1
    assert data["created"] == 0

    async with make_client() as client:
        products = (await client.get("/api/products/")).json()
        prod = [p for p in products if p["sku"] == "ST-1"][0]
        assert prod["price"] == 9000
        assert prod["name"] == "Стол обновлённый"


@pytest.mark.asyncio
async def test_import_auto_creates_supplier():
    async with make_client() as client:
        csv_text = (
            "name,sku,price,purchase_price,stock,unit,description,supplier\n"
            "Диван,DV-1,20000,15000,3,шт,,ООО Мебель\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200
    assert response.json()["created"] == 1

    async with make_client() as client:
        suppliers = (await client.get("/api/suppliers/")).json()
        assert len(suppliers) == 1
        assert suppliers[0]["contact_name"] == "ООО Мебель"

        products = (await client.get("/api/products/")).json()
        assert products[0]["supplier_name"] == "ООО Мебель"


@pytest.mark.asyncio
async def test_import_reuses_existing_supplier():
    async with make_client() as client:
        cid = int((await client.post("/api/contacts/", json={"name": "ООО Мебель"})).json()["id"])
        await client.post("/api/suppliers/", json={"contact_id": cid})

        csv_text = (
            "name,sku,price,purchase_price,stock,unit,description,supplier\n"
            "Диван,DV-1,20000,15000,3,шт,,ООО Мебель\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200

    async with make_client() as client:
        suppliers = (await client.get("/api/suppliers/")).json()
        assert len(suppliers) == 1


@pytest.mark.asyncio
async def test_import_skips_empty_name():
    async with make_client() as client:
        csv_text = (
            "name,sku,price\n"
            ",BAD-1,100\n"
            "Товар,OK-1,200\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_import_handles_comma_decimal():
    async with make_client() as client:
        csv_text = (
            "name,sku,price,purchase_price,stock,unit,description,supplier\n"
            "Товар,DEC-1,100,50,10,шт,,\n"
        )
        response = await _post_import(client, csv_text)
    assert response.status_code == 200

    async with make_client() as client:
        products = (await client.get("/api/products/")).json()
        assert products[0]["price"] == 100.0
