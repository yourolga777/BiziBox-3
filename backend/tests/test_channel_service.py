from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import InvalidToken

from app.services.channel_service import ChannelService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    return ChannelService(mock_session)


def _mock_settings_repo(tg: int = 10, email: int = 60) -> MagicMock:
    mock_repo = MagicMock()

    async def _get(key: str):
        return {
            "telegram_poll_interval": tg,
            "email_poll_interval": email,
        }.get(key)

    mock_repo.get = _get
    return mock_repo


@pytest.mark.asyncio
async def test_create_channel(service):
    service.repo.create = AsyncMock(return_value=MagicMock(id=1, type="telegram", name="Telegram"))
    result = await service.create(channel_type="telegram", name="Telegram")
    assert result.id == 1
    service.repo.create.assert_awaited_once_with(
        type="telegram", name="Telegram", config={}, is_connected=False,
    )


@pytest.mark.asyncio
async def test_update_channel(service):
    service.repo.update = AsyncMock(return_value=MagicMock(id=1, is_connected=True))
    result = await service.update(1, is_connected=True)
    assert result.is_connected is True
    service.repo.update.assert_awaited_once_with(1, is_connected=True)


@pytest.mark.asyncio
async def test_get_or_create_telegram_returns_existing_connected(service):
    connected = MagicMock(id=1, is_connected=True, config={})
    service.repo.get_by_type = AsyncMock(return_value=[connected, MagicMock(id=2, is_connected=False)])
    result = await service.get_or_create_telegram("+123")
    assert result.id == 1
    assert result.is_connected is True


@pytest.mark.asyncio
async def test_get_or_create_telegram_updates_existing_disconnected(service):
    existing = MagicMock(id=1, is_connected=False, config={"phone": "+123"})
    service.repo.get_by_type = AsyncMock(return_value=[existing])
    service.repo.update = AsyncMock()
    result = await service.get_or_create_telegram("+123")
    assert result.id == 1
    service.repo.update.assert_awaited_once_with(1, config={"phone": "+123"})


@pytest.mark.asyncio
async def test_get_or_create_telegram_creates_new(service):
    service.repo.get_by_type = AsyncMock(return_value=[])
    service.create = AsyncMock(return_value=MagicMock(id=3, type="telegram"))
    result = await service.get_or_create_telegram("+123")
    assert result.id == 3


@pytest.mark.asyncio
async def test_restore_channels_empty(service):
    service.repo.get_connected = AsyncMock(return_value=[])
    poll_service = MagicMock()
    await service.restore_channels(poll_service)
    poll_service.register_channel.assert_not_called()


@pytest.mark.asyncio
async def test_restore_channels_telegram(service):
    channel = MagicMock(
        type="telegram",
        config={"phone": "+123", "session_string": "abc"},
    )
    service.repo.get_connected = AsyncMock(return_value=[channel])
    poll_service = MagicMock()
    repo_mock = _mock_settings_repo(tg=10)

    with (
        patch("app.services.channel_service.TelegramAdapter") as mock_telegram,
        patch("app.services.channel_service.decrypt", return_value="decrypted_session"),
        patch("app.services.channel_service.SettingsRepository",
              return_value=repo_mock,
        ),
        patch(
            "app.services.channel_service.load_effective_telegram_config",
            return_value={"api_id": 12345, "api_hash": "hash", "proxy": None},
        ),
        patch("app.services.channel_service.settings") as mock_settings,
    ):
        mock_settings.TELEGRAM_POLL_INTERVAL = 30
        adapter_instance = AsyncMock()
        adapter_instance.connect.return_value = True
        mock_telegram.return_value = adapter_instance

        await service.restore_channels(poll_service)

        mock_telegram.assert_called_once()
        adapter_instance.connect.assert_awaited_once()
        poll_service.register_channel.assert_called_once_with(
            "telegram", adapter_instance,
        )
        poll_service.start.assert_called_once_with(
            "telegram", 10, since=channel.last_polled_at,
        )


@pytest.mark.asyncio
async def test_restore_channels_email(service):
    channel = MagicMock(
        type="email",
        config={"email": "test@test.com", "password": "encrypted_pass"},
    )
    service.repo.get_connected = AsyncMock(return_value=[channel])
    poll_service = MagicMock()
    repo_mock = _mock_settings_repo(email=60)

    with (
        patch("app.services.channel_service.EmailAdapter") as mock_email,
        patch("app.services.channel_service.decrypt", return_value="decrypted_pass"),
        patch("app.services.channel_service.SettingsRepository",
              return_value=repo_mock,
        ),
        patch("app.services.channel_service.settings") as mock_settings,
    ):
        mock_settings.EMAIL_POLL_INTERVAL = 120
        adapter_instance = AsyncMock()
        adapter_instance.connect.return_value = True
        mock_email.return_value = adapter_instance

        await service.restore_channels(poll_service)

        mock_email.assert_called_once()
        adapter_instance.connect.assert_awaited_once()
        poll_service.register_channel.assert_called_once_with("email", adapter_instance)
        poll_service.start.assert_called_once_with(
            "email", 60, since=channel.last_polled_at,
        )


@pytest.mark.asyncio
async def test_restore_channels_telegram_timeout(service):
    channel = MagicMock(
        type="telegram",
        config={"phone": "+123", "session_string": "abc"},
    )
    service.repo.get_connected = AsyncMock(return_value=[channel])
    poll_service = MagicMock()
    repo_mock = _mock_settings_repo()

    with (
        patch("app.services.channel_service.TelegramAdapter") as mock_telegram,
        patch("app.services.channel_service.decrypt", return_value="decrypted_session"),
        patch("app.services.channel_service.SettingsRepository",
              return_value=repo_mock,
        ),
        patch(
            "app.services.channel_service.load_effective_telegram_config",
            return_value={"api_id": 12345, "api_hash": "hash", "proxy": None},
        ),
        patch("app.services.channel_service.settings") as mock_settings,
    ):
        mock_settings.TELEGRAM_POLL_INTERVAL = 10
        adapter_instance = AsyncMock()
        adapter_instance.connect.side_effect = TimeoutError("timeout")
        mock_telegram.return_value = adapter_instance

        await service.restore_channels(poll_service)

        poll_service.register_channel.assert_not_called()


@pytest.mark.asyncio
async def test_restore_channels_timeout_sets_disconnected(service):
    channel = MagicMock(
        type="email",
        config={"email": "test@test.com", "password": "encrypted_pass"},
    )
    service.repo.get_connected = AsyncMock(return_value=[channel])
    service.repo.update = AsyncMock()
    poll_service = MagicMock()
    repo_mock = _mock_settings_repo()

    with (
        patch("app.services.channel_service.EmailAdapter") as mock_email,
        patch("app.services.channel_service.decrypt", return_value="decrypted_pass"),
        patch("app.services.channel_service.SettingsRepository",
              return_value=repo_mock,
        ),
        patch("app.services.channel_service.settings") as mock_settings,
    ):
        mock_settings.EMAIL_POLL_INTERVAL = 60
        adapter_instance = AsyncMock()
        adapter_instance.connect.side_effect = TimeoutError("timeout")
        mock_email.return_value = adapter_instance

        await service.restore_channels(poll_service)

        poll_service.register_channel.assert_not_called()
        service.repo.update.assert_called_once_with(channel.id, is_connected=False)


@pytest.mark.asyncio
async def test_restore_channels_decrypt_failure_sets_disconnected(service):
    channel = MagicMock(
        type="email",
        config={"email": "test@test.com", "password": "bad_encrypted_pass"},
    )
    service.repo.get_connected = AsyncMock(return_value=[channel])
    service.repo.update = AsyncMock()
    poll_service = MagicMock()
    repo_mock = _mock_settings_repo()

    with (
        patch("app.services.channel_service.EmailAdapter"),
        patch("app.services.channel_service.decrypt", side_effect=InvalidToken),
        patch("app.services.channel_service.SettingsRepository",
              return_value=repo_mock,
        ),
        patch("app.services.channel_service.settings") as mock_settings,
    ):
        mock_settings.EMAIL_POLL_INTERVAL = 60

        await service.restore_channels(poll_service)

        poll_service.register_channel.assert_not_called()
        service.repo.update.assert_awaited_once_with(channel.id, is_connected=False)


@pytest.mark.asyncio
async def test_reconnect_disconnected_telegram(service):
    channel = MagicMock(
        type="telegram",
        config={"session_string": "abc"},
        last_polled_at=None,
    )
    service.repo.get_disconnected = AsyncMock(return_value=[channel])
    service.repo.update = AsyncMock()
    poll_service = MagicMock()
    poll_service.is_running.return_value = False
    repo_mock = _mock_settings_repo(tg=10)
    adapter_instance = AsyncMock()
    service._connect_saved = AsyncMock(return_value=adapter_instance)

    with patch("app.services.channel_service.SettingsRepository", return_value=repo_mock):
        result = await service.reconnect_disconnected(poll_service)

    assert result == 1
    poll_service.register_channel.assert_called_once_with("telegram", adapter_instance)
    poll_service.start.assert_called_once_with("telegram", 10, since=channel.last_polled_at)
    service.repo.update.assert_awaited_once_with(channel.id, is_connected=True)


@pytest.mark.asyncio
async def test_reconnect_disconnected_skips_running(service):
    channel = MagicMock(type="telegram", config={})
    service.repo.get_disconnected = AsyncMock(return_value=[channel])
    poll_service = MagicMock()
    poll_service.is_running.return_value = True
    service._connect_saved = AsyncMock()

    result = await service.reconnect_disconnected(poll_service)

    assert result == 0
    service._connect_saved.assert_not_called()
    poll_service.register_channel.assert_not_called()


@pytest.mark.asyncio
async def test_reconnect_disconnected_connect_fails(service):
    channel = MagicMock(type="telegram", config={})
    service.repo.get_disconnected = AsyncMock(return_value=[channel])
    poll_service = MagicMock()
    poll_service.is_running.return_value = False
    service._connect_saved = AsyncMock(return_value=None)

    result = await service.reconnect_disconnected(poll_service)

    assert result == 0
    poll_service.register_channel.assert_not_called()
