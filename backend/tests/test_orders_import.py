import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_contact(client, name: str = "Client") -> int:
    response = await client.post("/api/contacts/", json={"name": name})
    return int(response.json()["id"])


async def _create_order(client, contact_id: int, **kwargs) -> int:
    payload = {
        "contact_id": contact_id,
        "items": [{"name": "Item", "quantity": 1, "price": 100}],
        **kwargs,
    }
    response = await client.post("/api/orders/", json=payload)
    assert response.status_code == 201
    return int(response.json()["id"])


async def _create_product(client, name: str = "Пицца Маргарита", price: float = 500.0) -> int:
    response = await client.post("/api/products/", json={
        "name": name,
        "price": price,
        "unit": "шт",
    })
    assert response.status_code == 201
    return int(response.json()["id"])


@pytest.mark.asyncio
async def test_order_numbers_sequential_increment():
    async with make_client() as client:
        cid = await _create_contact(client)
        first = await client.post("/api/orders/", json={
            "contact_id": cid, "items": [{"name": "A", "quantity": 1, "price": 10}],
        })
        second = await client.post("/api/orders/", json={
            "contact_id": cid, "items": [{"name": "B", "quantity": 1, "price": 20}],
        })
    n1 = first.json()["order_number"]
    n2 = second.json()["order_number"]
    assert n1 is not None and n2 is not None
    assert n1.startswith("ORD-")
    assert n2.startswith("ORD-")
    suffix1 = int(n1.rsplit("-", 1)[1])
    suffix2 = int(n2.rsplit("-", 1)[1])
    assert suffix2 == suffix1 + 1, f"ожидался последовательный номер, получено {n1} и {n2}"


@pytest.mark.asyncio
async def test_update_order_item_recalculates_total():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)
        order = (await client.get(f"/api/orders/{oid}")).json()
        item_id = order["items"][0]["id"]
        assert order["total"] == 100.0

        resp = await client.patch(f"/api/orders/{oid}/items/{item_id}", json={"quantity": 3, "price": 50})
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 3
        assert resp.json()["price"] == 50.0

        order2 = (await client.get(f"/api/orders/{oid}")).json()
        assert order2["total"] == 150.0


@pytest.mark.asyncio
async def test_update_order_item_404():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)
        resp = await client.patch(f"/api/orders/{oid}/items/999999", json={"price": 10})
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_orders_csv_creates_orders_and_contacts():
    async with make_client() as client:
        await _create_product(client, name="Пицца Маргарита", price=500.0)
        csv_content = (
            "\uFEFF№;Клиент;Товары;Сумма;Статус;Дата\n"
            "ORD-1;Иван;Пицца Маргарита x2;1000;Новый;2026-09-29 12:00\n"
            "ORD-2;Петя;Кофе x2;300;Отменён;2026-09-28 10:30\n"
        ).encode("utf-8")

        resp = await client.post(
            "/api/orders/import/csv",
            files={"file": ("orders.csv", csv_content, "text/csv")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["errors"] == []

    async with make_client() as client:
        orders = (await client.get("/api/orders/?limit=50")).json()
        contacts = (await client.get("/api/contacts/?limit=50")).json()
    contact_names = {c["name"] for c in contacts}
    assert "Иван" in contact_names
    assert "Петя" in contact_names

    by_contact = {o["contact_name"]: o for o in orders}
    ivan = by_contact.get("Иван")
    assert ivan is not None
    assert ivan["status"] == "new"
    assert ivan["total"] == 1000.0
    assert len(ivan["items"]) == 1
    assert ivan["items"][0]["name"] == "Пицца Маргарита"
    assert ivan["items"][0]["price"] == 500.0  # цена из каталога

    petya = by_contact.get("Петя")
    assert petya is not None
    assert petya["status"] == "cancelled"
    # один товар без каталога: цена = сумма / кол-во
    assert petya["items"][0]["price"] == 150.0


@pytest.mark.asyncio
async def test_import_orders_csv_empty_client_skipped_with_error():
    async with make_client() as client:
        csv_content = (
            "\uFEFF№;Клиент;Товары;Сумма;Статус;Дата\n"
            "ORD-1;Иван;Пицца x1;100;Новый;2026-09-29 12:00\n"
            "ORD-2;;Чай x1;50;Новый;2026-09-29 12:05\n"
        ).encode("utf-8")
        resp = await client.post(
            "/api/orders/import/csv",
            files={"file": ("orders.csv", csv_content, "text/csv")},
        )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
    assert resp.json()["skipped"] == 1
    assert any("строка 3" in e for e in resp.json()["errors"])


@pytest.mark.asyncio
async def test_orders_export_csv_uses_semicolon():
    async with make_client() as client:
        cid = await _create_contact(client)
        await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "Item, с запятой", "quantity": 1, "price": 10}],
        })
        resp = await client.get("/api/orders/export/csv")
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("\uFEFF№;Клиент;Товары;")
    lines = body.strip().splitlines()
    assert len(lines) >= 2
    # позиция с запятой остаётся внутри кавычек, а не делит колонки по ","
    assert ";Item, с запятой x1;" in lines[1] or lines[1].count(";") >= 5


@pytest.mark.asyncio
async def test_products_export_csv_uses_semicolon():
    async with make_client() as client:
        await _create_product(client, name="Товар;В")

        resp = await client.get("/api/products/export/csv")
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("\uFEFFid;name;sku;")
    assert ";Товар;В;" in body or "\"Товар;В\";" in body


@pytest.mark.asyncio
async def test_products_import_detects_semicolon_delimiter():
    async with make_client() as client:
        csv_content = (
            "\uFEFFname;sku;price;unit\n"
            "Товар А;A1;150;шт\n"
        ).encode("utf-8")
        resp = await client.post(
            "/api/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        products = (await client.get("/api/products/?limit=50")).json()
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
    assert any(p["name"] == "Товар А" and p["price"] == 150.0 for p in products)


@pytest.mark.asyncio
async def test_products_import_comma_delimiter_still_works():
    async with make_client() as client:
        csv_content = (
            "\uFEFFname,sku,price,unit\n"
            "Товар Б,B1,200,шт\n"
        ).encode("utf-8")
        resp = await client.post(
            "/api/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        products = (await client.get("/api/products/?limit=50")).json()
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
    assert any(p["name"] == "Товар Б" and p["price"] == 200.0 for p in products)


@pytest.mark.asyncio
async def test_product_permanent_delete_detaches_order_items():
    async with make_client() as client:
        cid = await _create_contact(client)
        pid = await _create_product(client, name="Удаляемый товар", price=100.0)

        order = await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "old-name", "product_id": pid, "quantity": 1, "price": 100}],
        })
        oid = order.json()["id"]

        resp = await client.delete(f"/api/products/{pid}/permanent")
        assert resp.status_code == 204

        by_id = await client.get(f"/api/products/{pid}")
        assert by_id.status_code == 404

        detail = (await client.get(f"/api/orders/{oid}")).json()
        assert detail["items"][0]["product_id"] is None


@pytest.mark.asyncio
async def test_product_permanent_delete_404():
    async with make_client() as client:
        resp = await client.delete("/api/products/999999/permanent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_order_delivery_date_defaults_and_roundtrip():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "A", "quantity": 1, "price": 10}],
            "delivery_date": "2026-10-10",
        })
        assert created.status_code == 201
        order = created.json()
        assert order["delivery_date"] == "2026-10-10"

        updated = await client.patch(f"/api/orders/{order['id']}", json={"delivery_date": "2026-10-12"})
        assert updated.status_code == 200
        assert updated.json()["delivery_date"] == "2026-10-12"


@pytest.mark.asyncio
async def test_product_autogenerates_sku_daily_sequence():
    async with make_client() as client:
        first = await client.post("/api/products/", json={"name": "Товар без артикула 1"})
        second = await client.post("/api/products/", json={"name": "Товар без артикула 2"})
    assert first.status_code == 201
    assert second.status_code == 201
    sku1 = first.json()["sku"]
    sku2 = second.json()["sku"]
    assert sku1 and sku2
    assert sku1.startswith("SKU-")
    assert sku2.startswith("SKU-")
    day1 = sku1.rsplit("-", 1)[0]
    day2 = sku2.rsplit("-", 1)[0]
    assert day1 == day2
    n1 = int(sku1.rsplit("-", 1)[1])
    n2 = int(sku2.rsplit("-", 1)[1])
    assert n2 == n1 + 1


@pytest.mark.asyncio
async def test_search_messages_by_contact_name():
    async with make_client() as client:
        cid = await _create_contact(client, "Иван Баринов")
        await client.post("/api/messages/", json={
            "contact_id": cid, "channel": "telegram", "content": "привет",
            "direction": "incoming", "status": "unread",
        })
        resp = await client.get("/api/messages/search", params={"q": "Баринов"})
    assert resp.status_code == 200
    results = resp.json()
    assert any(m["contact_id"] == cid for m in results)
