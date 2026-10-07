"""Регрессионный тест H1: кеш dashboard metrics изолирован по owner_id.

Без фикса (глобальный _cache на всех) второй запрос owner 1 вернул бы
данные owner 2 — тест это ловит. get_current_user всегда возвращает
DEFAULT_OWNER_ID, поэтому двух владельцев симулируем через
app.dependency_overrides.
"""

from types import SimpleNamespace

import pytest

from app.config import DEFAULT_OWNER_ID
from app.deps import get_current_user
from app.main import app
from app.repositories.contact import ContactRepository
from app.repositories.message import MessageRepository
from app.routers import dashboard
from tests.conftest import make_client


def _stub_owner(user_id: int):
    async def _dep():
        return SimpleNamespace(id=user_id)

    return _dep


@pytest.mark.asyncio
async def test_dashboard_metrics_cache_isolated_between_owners(db_session):
    dashboard._cache.clear()

    owner1 = DEFAULT_OWNER_ID
    owner2 = 2

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        c1 = await ContactRepository(session, owner_id=owner1).create(name="C1")
        c2 = await ContactRepository(session, owner_id=owner2).create(name="C2")
        m_repo1 = MessageRepository(session, owner_id=owner1)
        m_repo2 = MessageRepository(session, owner_id=owner2)
        for i in range(2):
            await m_repo1.create(
                contact_id=int(c1.id), channel="telegram", content=f"m1-{i}",
                direction="incoming", status="unread",
            )
        for i in range(5):
            await m_repo2.create(
                contact_id=int(c2.id), channel="telegram", content=f"m2-{i}",
                direction="incoming", status="unread",
            )
        await session.commit()

    try:
        app.dependency_overrides[get_current_user] = _stub_owner(owner1)
        async with make_client() as client:
            first = await client.get("/api/dashboard/metrics")
            assert first.status_code == 200
            assert first.json()["total_messages"] == 2

        app.dependency_overrides[get_current_user] = _stub_owner(owner2)
        async with make_client() as client:
            second = await client.get("/api/dashboard/metrics")
            assert second.status_code == 200
            assert second.json()["total_messages"] == 5

        app.dependency_overrides[get_current_user] = _stub_owner(owner1)
        async with make_client() as client:
            third = await client.get("/api/dashboard/metrics")
            assert third.status_code == 200
            assert third.json()["total_messages"] == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        dashboard._cache.clear()


@pytest.mark.asyncio
async def test_bulk_status_update_invalidates_metrics_cache(db_session):
    """Регрессия: после bulk/status unread_chats должен обновиться сразу,
    а не ждать CACHE_TTL (серверный кэш метрик сбрасывается)."""
    dashboard._cache.clear()
    owner = DEFAULT_OWNER_ID

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        c = await ContactRepository(session, owner_id=owner).create(name="C-bulk")
        m_repo = MessageRepository(session, owner_id=owner)
        msg = await m_repo.create(
            contact_id=int(c.id), channel="telegram", content="привет",
            direction="incoming", status="unread",
        )
        await session.commit()
        msg_id = int(msg.id)

    try:
        app.dependency_overrides[get_current_user] = _stub_owner(owner)
        async with make_client() as client:
            first = await client.get("/api/dashboard/metrics")
            assert first.status_code == 200
            assert first.json()["unread_chats"] == 1

            res = await client.patch(
                "/api/messages/bulk/status",
                json={"ids": [msg_id], "status": "read"},
            )
            assert res.status_code == 200
            assert res.json()["updated"] == 1

            # Без сброса кэша здесь было бы stale-значение unread_chats == 1
            second = await client.get("/api/dashboard/metrics")
            assert second.status_code == 200
            assert second.json()["unread_chats"] == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        dashboard._cache.clear()
