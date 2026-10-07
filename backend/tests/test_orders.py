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


@pytest.mark.asyncio
async def test_create_order():
    async with make_client() as client:
        cid = await _create_contact(client)

        response = await client.post("/api/orders/", json={
            "contact_id": cid,
            "delivery_address": "ул. Ленина, 10",
            "payment_method": "card",
            "items": [
                {"name": "Стул", "quantity": 2, "price": 4500},
                {"name": "Стол", "quantity": 1, "price": 8000},
            ],
        })
    assert response.status_code == 201
    data = response.json()
    assert data["contact_id"] == cid
    assert data["status"] == "new"
    assert data["total"] == 17000.0
    assert len(data["items"]) == 2
    assert data["order_number"] is not None
    assert data["paid"] is False
    assert data["comments"] == []


@pytest.mark.asyncio
async def test_create_order_with_contact_name():
    async with make_client() as client:
        response = await client.post("/api/orders/", json={
            "contact_name": "Иван Наставников",
            "contact_phone": "+79990000001",
            "items": [{"name": "Товар", "quantity": 1, "price": 100}],
        })
    assert response.status_code == 201
    data = response.json()
    assert data["contact_name"] == "Иван Наставников"
    assert data["total"] == 100.0


@pytest.mark.asyncio
async def test_create_order_without_contact_rejected():
    async with make_client() as client:
        response = await client.post("/api/orders/", json={
            "items": [{"name": "Товар", "quantity": 1, "price": 100}],
        })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_orders():
    async with make_client() as client:
        cid = await _create_contact(client)
        await _create_order(client, cid)
        await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "Item 2", "quantity": 1, "price": 200}],
        })

        response = await client.get("/api/orders/")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_get_order_by_id():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        response = await client.get(f"/api/orders/{oid}")
    assert response.status_code == 200
    assert response.json()["id"] == oid


@pytest.mark.asyncio
async def test_update_order():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        response = await client.patch(f"/api/orders/{oid}", json={"delivery_address": "Новый адрес"})
    assert response.status_code == 200
    assert response.json()["delivery_address"] == "Новый адрес"


@pytest.mark.asyncio
async def test_update_order_paid():
    async with make_client() as client:
        cid = await _create_contact(client)
        created = await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "Item", "quantity": 1, "price": 100}],
        })
        oid = created.json()["id"]
        assert created.json()["paid"] is False

        response = await client.patch(f"/api/orders/{oid}", json={"paid": True})
    assert response.status_code == 200
    assert response.json()["paid"] is True


@pytest.mark.asyncio
async def test_delete_order():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        response = await client.delete(f"/api/orders/{oid}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_restore_order():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)
        await client.delete(f"/api/orders/{oid}")

        response = await client.post(f"/api/orders/{oid}/restore")
    assert response.status_code == 200
    assert response.json()["id"] == oid


@pytest.mark.asyncio
async def test_order_status_update():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        response = await client.patch(f"/api/orders/{oid}/status", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_order_invalid_status():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        response = await client.patch(f"/api/orders/{oid}/status", json={"status": "invalid_status"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_order_filter_by_status():
    async with make_client() as client:
        cid = await _create_contact(client)
        o1 = await _create_order(client, cid)
        await client.patch(f"/api/orders/{o1}/status", json={"status": "completed"})
        await _create_order(client, cid)

        completed = await client.get("/api/orders/?status=completed")
        new = await client.get("/api/orders/?status=new")
    assert len(completed.json()) >= 1
    assert len(new.json()) >= 1


@pytest.mark.asyncio
async def test_order_search():
    async with make_client() as client:
        cid = await _create_contact(client, name="Иван Клиентов")
        created = await client.post("/api/orders/", json={
            "contact_id": cid,
            "items": [{"name": "Item", "quantity": 1, "price": 100}],
        })
        order_number = created.json()["order_number"]

        by_number = await client.get(f"/api/orders/?search={order_number}")
        by_name = await client.get("/api/orders/?search=Клиентов")
    assert len(by_number.json()) >= 1
    assert len(by_name.json()) >= 1


@pytest.mark.asyncio
async def test_order_add_remove_item():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        add_resp = await client.post(f"/api/orders/{oid}/items", json={
            "name": "Added", "quantity": 2, "price": 50,
        })
        assert add_resp.status_code == 201
        item_id = add_resp.json()["id"]

        order = await client.get(f"/api/orders/{oid}")
        assert order.json()["total"] == 200.0

        del_resp = await client.delete(f"/api/orders/{oid}/items/{item_id}")
        assert del_resp.status_code == 204

        order2 = await client.get(f"/api/orders/{oid}")
        assert order2.json()["total"] == 100.0


@pytest.mark.asyncio
async def test_order_add_comment():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)

        add_resp = await client.post(f"/api/orders/{oid}/comments", json={"content": "Перезвонить клиенту"})
        assert add_resp.status_code == 201

        comments_resp = await client.get(f"/api/orders/{oid}/comments")
    assert comments_resp.status_code == 200
    assert len(comments_resp.json()) == 1
    assert comments_resp.json()[0]["content"] == "Перезвонить клиенту"


@pytest.mark.asyncio
async def test_order_delete_comment():
    async with make_client() as client:
        cid = await _create_contact(client)
        oid = await _create_order(client, cid)
        comment = await client.post(f"/api/orders/{oid}/comments", json={"content": "Удалить"})
        comment_id = comment.json()["id"]

        del_resp = await client.delete(f"/api/orders/{oid}/comments/{comment_id}")
        assert del_resp.status_code == 204

        comments_resp = await client.get(f"/api/orders/{oid}/comments")
    assert comments_resp.json() == []


@pytest.mark.asyncio
async def test_suggest_order_from_message():
    async with make_client() as client:
        cid = await _create_contact(client, name="Покупатель")
        msg = await client.post(
            "/api/messages/",
            json={
                "contact_id": cid,
                "channel": "telegram",
                "content": "Хочу заказать, стоимость 2500 руб",
                "direction": "incoming",
            },
        )
        message_id = msg.json()["id"]

        response = await client.post(f"/api/orders/suggest/{message_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["contact_id"] == cid
    assert data["contact_name"] == "Покупатель"
    assert data["suggested_amount"] == 2500.0
    assert "Хочу заказать" in data["message_preview"]


@pytest.mark.asyncio
async def test_suggest_order_message_not_found():
    async with make_client() as client:
        response = await client.post("/api/orders/suggest/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_order_rolls_back_on_item_failure(monkeypatch):
    """Сбой при создании item — заказ не создан."""
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import OrderModel
    from app.services.order_service import OrderService

    async with AsyncSessionLocal() as session:
        service = OrderService(session)
        contact = await service.contact_repo.create(
            name="RollbackTest", phone="+79990000001"
        )
        cid = int(contact.id)
        await session.commit()

    async with AsyncSessionLocal() as session:
        service = OrderService(session)
        original_create = service.item_repo.create
        counter = [0]

        async def _fail_on_2nd(**kwargs):
            counter[0] += 1
            if counter[0] == 2:
                raise RuntimeError("injected item creation failure")
            return await original_create(**kwargs)

        monkeypatch.setattr(service.item_repo, "create", _fail_on_2nd)

        from app.schemas.order import OrderCreate, OrderItemCreate

        with pytest.raises(RuntimeError):
            await service.create(OrderCreate(
                contact_id=cid,
                items=[
                    OrderItemCreate(name="Item1", quantity=1, price=100),
                    OrderItemCreate(name="Item2", quantity=2, price=200),
                    OrderItemCreate(name="Item3", quantity=1, price=50),
                ],
            ))

        await session.rollback()

    async with AsyncSessionLocal() as session:
        orders = await session.scalar(select(func.count(OrderModel.id)))
        assert orders == 0, f"заказов должно быть 0 после отката, есть {orders}"
