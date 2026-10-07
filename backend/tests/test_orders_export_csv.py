import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_export_orders_csv_headers():
    async with make_client() as client:
        response = await client.get("/api/orders/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_orders_csv_contains_bom():
    async with make_client() as client:
        response = await client.get("/api/orders/export/csv")
    assert "\uFEFF" in response.text


@pytest.mark.asyncio
async def test_export_orders_csv_contains_data():
    async with make_client() as client:
        contact_resp = await client.post(
            "/api/contacts/", json={"name": "CSV-клиент", "phone": "+75555555555"}
        )
        contact_id = contact_resp.json()["id"]

        order_resp = await client.post(
            "/api/orders/",
            json={
                "contact_id": contact_id,
                "items": [{"name": "CSV-товар", "quantity": 2, "price": 300}],
            },
        )
        order_number = order_resp.json()["order_number"]

        response = await client.get("/api/orders/export/csv")
    content = response.text
    assert order_number in content
    assert "CSV-клиент" in content
    assert "CSV-товар" in content
    assert "600" in content
    assert "Новый" in content
