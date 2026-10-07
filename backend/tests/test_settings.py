import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.database import AsyncSessionLocal, init_db
from app.repositories.settings import SettingsRepository
from tests.conftest import make_client, make_transport


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)
    async with AsyncSessionLocal() as session:
        repo = SettingsRepository(session)
        await repo.set("telegram_poll_interval", 10)
        await repo.set("email_poll_interval", 60)
        await repo.set("theme", "light")
        await session.commit()


_uniq = uuid.uuid4().hex[:6]


@pytest.mark.asyncio
async def test_get_settings_returns_defaults():
    async with make_client() as client:
        response = await client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_poll_interval"] == 10
    assert data["email_poll_interval"] == 60
    assert data["theme"] == "light"


@pytest.mark.asyncio
async def test_patch_settings_updates_values():
    async with make_client() as client:
        response = await client.patch(
            "/api/settings/",
            json={"values": {"telegram_poll_interval": 30, "theme": "dark"}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_poll_interval"] == 30
    assert data["theme"] == "dark"


@pytest.mark.asyncio
async def test_persist_settings_across_requests():
    async with make_client() as client:
        await client.patch(
            "/api/settings/",
            json={"values": {"email_poll_interval": 120}},
        )

        response = await client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert data["email_poll_interval"] == 120


@pytest.mark.asyncio
async def test_partial_update_keeps_other_values():
    async with make_client() as client:
        await client.patch(
            "/api/settings/",
            json={"values": {"telegram_poll_interval": 20, "email_poll_interval": 150}},
        )

        response = await client.get("/api/settings/")
    data = response.json()
    assert data["email_poll_interval"] == 150
    assert data["telegram_poll_interval"] == 20
    assert data["theme"] == "light"


@pytest.mark.asyncio
async def test_patch_restarts_polling_on_interval_change():
    poll_service = MagicMock()
    adapter = AsyncMock()
    poll_service.get_channel.return_value = adapter
    poll_service.stop = AsyncMock()
    poll_service.start = MagicMock()

    transport = make_transport()
    with patch("app.deps.get_poll_service", return_value=poll_service):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/settings/",
                json={"values": {"telegram_poll_interval": 30}},
            )

    assert response.status_code == 200
    poll_service.stop.assert_awaited_once_with("telegram")
    poll_service.start.assert_called_once_with("telegram", 30)


@pytest.mark.asyncio
async def test_patch_does_not_restart_without_adapter():
    poll_service = MagicMock()
    poll_service.get_channel.return_value = None

    transport = make_transport()
    with patch("app.deps.get_poll_service", return_value=poll_service):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/settings/",
                json={"values": {"email_poll_interval": 90}},
            )

    assert response.status_code == 200
    poll_service.stop.assert_not_called()
    poll_service.start.assert_not_called()


@pytest.mark.asyncio
async def test_patch_does_not_restart_when_interval_unchanged():
    poll_service = MagicMock()
    adapter = AsyncMock()
    poll_service.get_channel.return_value = adapter

    transport = make_transport()
    with patch("app.deps.get_poll_service", return_value=poll_service):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/settings/",
                json={"values": {"telegram_poll_interval": 10}},
            )

    assert response.status_code == 200
    poll_service.stop.assert_not_called()
    poll_service.start.assert_not_called()
