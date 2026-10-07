import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.channels.base import ChannelFetchTimeoutError
from app.services.poll_service import PollService


@pytest.fixture
def mock_session_factory():
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    factory = MagicMock(return_value=session)
    return factory, session


@pytest.fixture
def mock_cms():
    return MagicMock(return_value=AsyncMock())


@pytest.mark.asyncio
async def test_init_defaults():
    service = PollService()
    assert service._session_factory is None
    assert service._cms_factory is None
    assert service.channels == {}
    assert service.tasks == {}
    assert service.last_poll == {}


@pytest.mark.asyncio
async def test_init_with_injected_deps(mock_session_factory, mock_cms):
    factory, _ = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    assert service._session_factory is factory
    assert service._cms_factory is mock_cms


@pytest.mark.asyncio
async def test_register_and_get_channel():
    service = PollService()
    adapter = AsyncMock()
    service.register_channel("telegram", adapter)
    assert service.get_channel("telegram") is adapter
    assert service.get_channel("email") is None


@pytest.mark.asyncio
async def test_start_and_stop():
    service = PollService()
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = []
    service.register_channel("telegram", adapter)
    service.start("telegram", interval=1)
    assert "telegram" in service.tasks
    assert not service.tasks["telegram"].done()
    await service.stop("telegram")
    assert "telegram" not in service.tasks


@pytest.mark.asyncio
async def test_stop_all():
    service = PollService()
    for ch in ["a", "b"]:
        adapter = AsyncMock()
        adapter.fetch_messages.return_value = []
        service.register_channel(ch, adapter)
        service.start(ch, interval=1)
    await service.stop_all()
    assert service.tasks == {}


@pytest.mark.asyncio
async def test_poll_channel_no_adapter_stops():
    service = PollService()
    await service.poll_channel("nonexistent", interval=1)


@pytest.mark.asyncio
async def test_poll_channel_processes_incoming(mock_session_factory, mock_cms):
    factory, session = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {"direction": "incoming", "channel": "telegram", "message_id": "1", "content": "hi"},
    ]
    service.register_channel("telegram", adapter)

    task = asyncio.create_task(service.poll_channel("telegram", interval=999))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    cms_instance = mock_cms.return_value
    cms_instance.process_incoming.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_channel_processes_outgoing(mock_session_factory, mock_cms):
    factory, session = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {"direction": "outgoing", "channel": "telegram", "message_id": "2", "content": "out"},
    ]
    service.register_channel("telegram", adapter)

    task = asyncio.create_task(service.poll_channel("telegram", interval=999))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    cms_instance = mock_cms.return_value
    cms_instance.process_incoming.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_channel_processes_message_without_direction(mock_session_factory, mock_cms):
    factory, session = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = [
        {"channel": "telegram", "message_id": "3", "content": "no direction"},
    ]
    service.register_channel("telegram", adapter)

    task = asyncio.create_task(service.poll_channel("telegram", interval=999))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    cms_instance = mock_cms.return_value
    cms_instance.process_incoming.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_factory_fallback():
    service = PollService()
    from app.database import AsyncSessionLocal
    assert service._get_session_factory() is AsyncSessionLocal


@pytest.mark.asyncio
async def test_get_cms_factory_fallback():
    service = PollService()
    from app.services.channel_message_service import ChannelMessageService
    assert service._get_cms_factory() is ChannelMessageService


@pytest.mark.asyncio
async def test_start_accepts_initial_since():
    from datetime import datetime

    service = PollService()
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = []
    service.register_channel("telegram", adapter)

    ts = datetime(2026, 1, 1, 12, 0)
    service.start("telegram", interval=1, since=ts)
    assert service.last_poll["telegram"] == ts
    await service.stop("telegram")


def _stamp_calls(session):
    return [
        c for c in session.execute.await_args_list
        if "last_polled_at = :ts" in str(c.args[0])
    ]


@pytest.mark.asyncio
async def test_poll_channel_stamps_last_polled_after_success(mock_session_factory, mock_cms):
    factory, session = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    adapter = AsyncMock()
    adapter.fetch_messages.return_value = []
    service.register_channel("telegram", adapter)

    task = asyncio.create_task(service.poll_channel("telegram", interval=999))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(_stamp_calls(session)) == 1


@pytest.mark.asyncio
async def test_poll_channel_does_not_stamp_last_polled_on_timeout(mock_session_factory, mock_cms):
    factory, session = mock_session_factory
    service = PollService(session_factory=factory, cms_factory=mock_cms)
    adapter = AsyncMock()
    adapter.fetch_messages.side_effect = ChannelFetchTimeoutError("timeout")
    service.register_channel("telegram", adapter)

    task = asyncio.create_task(service.poll_channel("telegram", interval=999))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert _stamp_calls(session) == []
