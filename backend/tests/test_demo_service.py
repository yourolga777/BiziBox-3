"""Тесты демо-режима: предзаполнение данных по всем разделам."""

import pytest
from sqlalchemy import func, select

from app.config import DEFAULT_OWNER_ID
from app.models import (
    CalendarEventModel,
    ContactModel,
    MessageModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    SupplierModel,
    TaskModel,
    UserModel,
)
from app.services.demo_service import seed_demo_data


async def _count(session, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar() or 0


async def _ensure_demo_user(session) -> None:
    if await session.get(UserModel, DEFAULT_OWNER_ID) is None:
        session.add(UserModel(id=DEFAULT_OWNER_ID, username="demo", password_hash=""))
        await session.flush()


@pytest.mark.asyncio
async def test_seed_demo_data_populates_all_sections(db_session):
    await _ensure_demo_user(db_session)

    await seed_demo_data(db_session)
    await db_session.commit()

    assert await _count(db_session, ContactModel) >= 10
    assert await _count(db_session, MessageModel) >= 16
    assert await _count(db_session, TaskModel) >= 9
    assert await _count(db_session, OrderModel) >= 6
    assert await _count(db_session, OrderItemModel) >= 6
    assert await _count(db_session, ProductModel) >= 7
    assert await _count(db_session, SupplierModel) >= 2
    assert await _count(db_session, CalendarEventModel) >= 4


@pytest.mark.asyncio
async def test_seed_demo_data_has_vk_messages(db_session):
    await _ensure_demo_user(db_session)

    await seed_demo_data(db_session)
    await db_session.commit()

    vk_msgs = (await db_session.execute(
        select(MessageModel).where(MessageModel.channel == "vk")
    )).scalars().all()
    assert len(vk_msgs) >= 2
    assert any(m.direction == "incoming" for m in vk_msgs)


@pytest.mark.asyncio
async def test_seed_demo_data_orders_have_valid_statuses_and_items(db_session):
    await _ensure_demo_user(db_session)

    await seed_demo_data(db_session)
    await db_session.commit()

    orders = (await db_session.execute(select(OrderModel))).scalars().all()
    assert orders
    valid = {"new", "in_progress", "shipped", "completed", "cancelled"}
    assert all(o.status in valid for o in orders)

    items = (await db_session.execute(select(OrderItemModel))).scalars().all()
    assert items
    order_ids = {o.id for o in orders}
    assert all(i.order_id in order_ids for i in items)

    products = (await db_session.execute(select(ProductModel))).scalars().all()
    skus = [p.sku for p in products if p.sku]
    assert len(skus) == len(set(skus))


@pytest.mark.asyncio
async def test_demo_endpoint_returns_login(monkeypatch):
    from tests.conftest import make_client

    async def fake_activate_demo():
        return {"onboarded": True, "login": "demo"}

    monkeypatch.setattr("app.services.demo_service.activate_demo", fake_activate_demo)

    async with make_client() as client:
        response = await client.post("/api/settings/demo")

    assert response.status_code == 200
    data = response.json()
    assert data["onboarded"] is True
    assert data["login"] == "demo"
