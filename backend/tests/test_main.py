import pytest

from app.database import init_db
from app.version import VERSION
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_health():
    async with make_client() as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == VERSION
    assert data["app"] == "BiziBox"


@pytest.mark.asyncio
async def test_messages():
    async with make_client() as client:
        response = await client.get("/api/messages/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_contacts():
    async with make_client() as client:
        response = await client.get("/api/contacts/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tasks():
    async with make_client() as client:
        response = await client.get("/api/tasks/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_channels():
    async with make_client() as client:
        response = await client.get("/api/channels/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_startup_load_empty():
    async with make_client() as client:
        response = await client.post("/api/startup/load")
    assert response.status_code == 200
    data = response.json()
    assert "channels" in data
    assert "total_new" in data
    assert isinstance(data["channels"], list)
    assert data["total_new"] == 0


@pytest.mark.asyncio
async def test_download_messages_processes_outgoing():
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.database import AsyncSessionLocal
    from app.repositories.channel import ChannelRepository

    async with AsyncSessionLocal() as session:
        repo = ChannelRepository(session)
        await repo.create(
            type="telegram",
            name="Telegram",
            config={},
            is_connected=True,
        )
        await session.commit()

    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {
            "direction": "outgoing",
            "channel": "telegram",
            "contact_id": "12345",
            "message_id": "out_1",
            "content": "My sent message",
        },
    ]

    ps = MagicMock()
    ps.get_channel.return_value = adapter

    async with make_client() as client:
        with patch("app.routers.channels.base.get_poll_service", return_value=ps):
            response = await client.post("/api/channels/telegram/download")

    assert response.status_code == 200
    data = response.json()
    assert data["new_messages"] == 1


@pytest.mark.asyncio
async def test_dashboard_metrics():
    async with make_client() as client:
        response = await client.get("/api/dashboard/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_messages_today" in data
    assert "total_tasks_today" in data
