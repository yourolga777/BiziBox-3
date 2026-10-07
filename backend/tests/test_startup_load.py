from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.channel_service import ChannelService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    return ChannelService(mock_session)


async def _make_service(service, channels):
    service.repo.get_all = AsyncMock(return_value=channels)
    return service


@pytest.mark.asyncio
async def test_startup_load_no_channels(service):
    await _make_service(service, [])
    poll_service = MagicMock()
    result = await service.startup_load(poll_service)
    assert result["total_new"] == 0
    assert result["channels"] == []


@pytest.mark.asyncio
async def test_startup_load_reuses_running_adapter(service):
    channel = MagicMock(type="telegram", name="Telegram", config={"phone": "+123"})
    await _make_service(service, [channel])

    poll_service = MagicMock()
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = []
    poll_service.get_channel.return_value = adapter

    result = await service.startup_load(poll_service)

    poll_service.register_channel.assert_not_called()
    assert result["channels"][0]["connected"] is True
    assert result["channels"][0]["new_messages"] == 0
    assert result["total_new"] == 0


@pytest.mark.asyncio
async def test_startup_load_connects_saved_email(service):
    channel = MagicMock(
        type="email",
        name="test@test.com",
        config={"email": "test@test.com", "password": "plain_pass"},
    )
    await _make_service(service, [channel])

    poll_service = MagicMock()
    poll_service.get_channel.return_value = None

    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {
            "direction": "incoming",
            "channel": "email",
            "contact_id": "sender@test.com",
            "message_id": "1",
            "content": "Hello",
            "created_at": None,
        },
    ]

    cms = AsyncMock()
    cms.process_incoming.return_value = MagicMock()

    with (
        patch("app.services.channel_service.EmailAdapter", return_value=adapter),
        patch("app.services.channel_service.ChannelMessageService", return_value=cms),
    ):
        result = await service.startup_load(poll_service)

    assert result["channels"][0]["connected"] is True
    assert result["channels"][0]["new_messages"] == 1
    assert result["total_new"] == 1
    poll_service.register_channel.assert_called_once_with("email", adapter)
    adapter.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_load_processes_outgoing(service):
    channel = MagicMock(
        type="email",
        name="test@test.com",
        config={"email": "test@test.com", "password": "plain_pass"},
    )
    await _make_service(service, [channel])

    poll_service = MagicMock()
    poll_service.get_channel.return_value = None

    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {
            "direction": "outgoing",
            "channel": "email",
            "contact_id": "me@test.com",
            "message_id": "out_1",
            "content": "My sent mail",
            "created_at": None,
        },
    ]

    cms = AsyncMock()
    cms.process_incoming.return_value = MagicMock()

    with (
        patch("app.services.channel_service.EmailAdapter", return_value=adapter),
        patch("app.services.channel_service.ChannelMessageService", return_value=cms),
    ):
        result = await service.startup_load(poll_service)

    assert result["channels"][0]["new_messages"] == 1
    assert result["total_new"] == 1
    cms.process_incoming.assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_load_email_connect_failure(service):
    channel = MagicMock(
        type="email",
        name="test@test.com",
        config={"email": "test@test.com", "password": "plain_pass"},
    )
    await _make_service(service, [channel])

    poll_service = MagicMock()
    poll_service.get_channel.return_value = None

    adapter = AsyncMock()
    adapter.connect.return_value = False

    with patch("app.services.channel_service.EmailAdapter", return_value=adapter):
        result = await service.startup_load(poll_service)

    entry = result["channels"][0]
    assert entry["connected"] is False
    assert entry["new_messages"] == 0
    assert result["total_new"] == 0


@pytest.mark.asyncio
async def test_startup_load_one_channel_error_keeps_others(service):
    bad_channel = MagicMock(
        type="telegram",
        name="Telegram",
        config={"phone": "+123", "session_string": "abc"},
    )
    good_channel = MagicMock(
        type="email",
        name="good@test.com",
        config={"email": "good@test.com", "password": "pass"},
    )
    await _make_service(service, [bad_channel, good_channel])

    poll_service = MagicMock()
    poll_service.get_channel.side_effect = lambda t: None if t == "telegram" else None

    bad_adapter = AsyncMock()
    bad_adapter.connect.side_effect = RuntimeError("connect boom")

    good_adapter = AsyncMock()
    good_adapter.connect.return_value = True
    good_adapter.fetch_messages.return_value = []

    with (
        patch(
            "app.services.channel_service.TelegramAdapter",
            return_value=bad_adapter,
        ),
        patch(
            "app.services.channel_service.EmailAdapter",
            return_value=good_adapter,
        ),
    ):
        result = await service.startup_load(poll_service)

    assert len(result["channels"]) == 2
    assert result["channels"][0]["connected"] is False
    assert result["channels"][0]["error"] is not None
    assert result["channels"][1]["connected"] is True


@pytest.mark.asyncio
async def test_startup_load_no_session_string_telegram(service):
    channel = MagicMock(
        type="telegram",
        name="Telegram",
        config={"phone": "+123"},
    )
    await _make_service(service, [channel])

    poll_service = MagicMock()
    poll_service.get_channel.return_value = None

    result = await service.startup_load(poll_service)

    assert result["channels"][0]["connected"] is False
    assert result["total_new"] == 0
