from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.channels.telegram import TelegramAdapter
from app.database import init_db
from app.schemas.message import MessageResponse
from app.services.channel_message_service import ChannelMessageService


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    return ChannelMessageService(mock_session)


@pytest.mark.asyncio
async def test_register_and_get_channel(service):
    adapter = AsyncMock(spec=TelegramAdapter)
    service.register_channel("telegram", adapter)
    assert service.get_channel("telegram") is adapter
    assert "telegram" in service.get_all_channels()


@pytest.mark.asyncio
async def test_process_incoming_new_message(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=100))

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_1",
        "content": "Hello",
        "contact_name": "John",
    })

    assert result.id == 100
    service.contact_repo.get_or_create.assert_awaited_once_with(
        name="John", channel="telegram", channel_id="12345", telegram_username=None,
    )
    service.message_service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_incoming_passes_telegram_username(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=102))

    await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_3",
        "content": "Hello",
        "contact_name": "John",
        "contact_username": "alice",
    })

    service.contact_repo.get_or_create.assert_awaited_once_with(
        name="John", channel="telegram", channel_id="12345", telegram_username="alice",
    )


@pytest.mark.asyncio
async def test_process_incoming_links_pending_outgoing_on_race(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    pending = MagicMock(
        id=200, channel="telegram", channel_message_id=None, reply_to=None, subject=None,
        content="My reply", direction="outgoing", status="read",
        contact=None, contact_name=None, contact_username=None,
        content_html=None, extracted_code=None,
        is_flagged=False, is_pinned=False, snoozed_until=None,
        created_at=None, updated_at=None, attachments=[],
    )
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_repo.get_pending_outgoing = AsyncMock(return_value=pending)
    service.message_repo.update = AsyncMock(return_value=pending)
    service.message_service.create = AsyncMock()
    service.session.commit = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "race_1",
        "content": "My reply",
        "direction": "outgoing",
        "contact_name": "John",
    })

    assert result.id == 200
    service.message_repo.update.assert_awaited_once_with(200, channel_message_id="race_1")
    service.message_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_skips_duplicate(service):
    existing = MagicMock(
        id=50, channel="telegram", channel_message_id="dup_1",
        content="Duplicate", direction="incoming", status="unread",
        contact=None, contact_name=None, contact_username=None,
        reply_to=None, subject=None, extracted_code=None, content_html=None,
    )
    service.message_repo.get_by_channel_message = AsyncMock(return_value=existing)
    service.contact_repo.get_or_create = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "dup_1",
        "content": "Duplicate",
    })

    assert result.id == 50
    service.contact_repo.get_or_create.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_preserves_outgoing_direction(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_repo.get_pending_outgoing = AsyncMock(return_value=None)
    created = MagicMock(id=100)
    service.message_service.create = AsyncMock(return_value=created)

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_out_1",
        "content": "My reply",
        "direction": "outgoing",
        "contact_name": "John",
    })

    assert result.id == 100
    call = service.message_service.create.call_args[0][0]
    assert call.direction == "outgoing"
    assert call.status == "read"


@pytest.mark.asyncio
async def test_process_incoming_defaults_to_incoming_when_direction_missing(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    created = MagicMock(id=101)
    service.message_service.create = AsyncMock(return_value=created)

    await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_default_1",
        "content": "Hello",
        "contact_name": "John",
    })

    call = service.message_service.create.call_args[0][0]
    assert call.direction == "incoming"


@pytest.mark.asyncio
async def test_process_incoming_updates_direction_on_duplicate(service):
    existing = MagicMock(
        id=50, channel="telegram", channel_message_id="dup_2",
        content="Duplicate", direction="incoming", status="unread",
        contact=None, contact_name=None, contact_username=None,
        reply_to=None, subject=None, extracted_code=None, content_html=None,
    )
    updated = MagicMock(
        id=50, channel="telegram", channel_message_id="dup_2",
        content="Duplicate", direction="outgoing", status="unread",
        contact=None, contact_name=None, contact_username=None,
        reply_to=None, subject=None, extracted_code=None, content_html=None,
    )
    service.message_repo.get_by_channel_message = AsyncMock(return_value=existing)
    service.message_repo.update = AsyncMock(return_value=updated)
    service.contact_repo.get_or_create = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "dup_2",
        "content": "Duplicate",
        "direction": "outgoing",
    })

    assert result.id == 50
    assert result.direction == "outgoing"
    service.message_repo.update.assert_awaited_once_with(50, direction="outgoing")
    service.contact_repo.get_or_create.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_skips_duplicate_when_direction_matches(service):
    existing = MagicMock(
        id=51, channel="telegram", channel_message_id="dup_3",
        content="Duplicate", direction="incoming", status="unread",
        contact=None, contact_name=None, contact_username=None,
        reply_to=None, subject=None, extracted_code=None, content_html=None,
    )
    service.message_repo.get_by_channel_message = AsyncMock(return_value=existing)
    service.message_repo.update = AsyncMock()
    service.contact_repo.get_or_create = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "dup_3",
        "content": "Duplicate",
        "direction": "incoming",
    })

    assert result.id == 51
    assert result.direction == "incoming"
    service.message_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_send_reply_with_registered_adapter(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    original = MagicMock(id=1, channel="telegram", contact_id=10, channel_message_id=None)
    service.message_repo.get_by_id = AsyncMock(return_value=original)
    service.contact_repo.get_by_id = AsyncMock(return_value=MagicMock(id=10, telegram_id="12345", email=None))
    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_1"}
    service.register_channel("telegram", adapter)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=200))
    service.contact_repo.update = AsyncMock()

    fake_outbox = MagicMock()
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=999))
    fake_outbox.attempt_delivery = AsyncMock(return_value={"message_id": "sent_1"})
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    result = await service.send_reply(1, "Hello back")

    assert result.id == 200
    assert result.channel_message_id == "sent_1"
    fake_outbox.enqueue.assert_awaited_once()
    fake_outbox.attempt_delivery.assert_awaited_once()
    service.contact_repo.update.assert_awaited_once_with(10, is_known=True)


@pytest.mark.asyncio
async def test_send_reply_no_adapter_raises_503(service):
    original = MagicMock(id=1, channel="telegram", contact_id=10)
    service.message_repo.get_by_id = AsyncMock(return_value=original)

    with pytest.raises(HTTPException) as exc:
        await service.send_reply(1, "Hello")

    assert exc.value.status_code == 503
    assert "канал" in exc.value.detail.lower() or "Channel" in exc.value.detail


@pytest.mark.asyncio
async def test_send_reply_no_channel_id_raises_400(service):
    original = MagicMock(id=1, channel="telegram", contact_id=10)
    service.message_repo.get_by_id = AsyncMock(return_value=original)
    service.contact_repo.get_by_id = AsyncMock(return_value=MagicMock(id=10, telegram_id=None, email=None))
    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_1"}
    service.register_channel("telegram", adapter)

    with pytest.raises(HTTPException) as exc:
        await service.send_reply(1, "Hello")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_send_message_with_recipient_uses_it(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    service.contact_repo.get_by_id = AsyncMock(
        return_value=MagicMock(id=10, telegram_id="12345", email=None)
    )
    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_1"}
    service.register_channel("telegram", adapter)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=300))
    service.message_repo.get_by_id = AsyncMock(return_value=None)
    service.contact_repo.update = AsyncMock()

    fake_outbox = MagicMock()
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=1000))
    fake_outbox.attempt_delivery = AsyncMock(return_value=None)
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    result = await service.send_message(
        contact_id=10, channel="telegram", content="Hi", recipient="999888777"
    )

    assert result.id == 300
    assert fake_outbox.enqueue.call_args.kwargs["channel_id"] == "999888777"


@pytest.mark.asyncio
async def test_send_message_with_username_recipient_resolves(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    service.contact_repo.get_by_id = AsyncMock(
        return_value=MagicMock(id=10, telegram_id="12345", email=None)
    )
    adapter = AsyncMock()
    adapter.resolve_channel_id = AsyncMock(return_value="555666")
    adapter.send_message.return_value = {"message_id": "sent_2"}
    service.register_channel("telegram", adapter)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=301))
    service.message_repo.get_by_id = AsyncMock(return_value=None)
    service.contact_repo.update = AsyncMock()

    fake_outbox = MagicMock()
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=1001))
    fake_outbox.attempt_delivery = AsyncMock(return_value=None)
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    result = await service.send_message(
        contact_id=10, channel="telegram", content="Hi", recipient="@alice"
    )

    assert result.id == 301
    adapter.resolve_channel_id.assert_awaited_once_with("@alice")
    assert fake_outbox.enqueue.call_args.kwargs["channel_id"] == "555666"


@pytest.mark.asyncio
async def test_send_message_unresolvable_recipient_raises_400(service):
    service.contact_repo.get_by_id = AsyncMock(
        return_value=MagicMock(id=10, telegram_id="12345", email=None)
    )
    adapter = AsyncMock()
    adapter.resolve_channel_id = AsyncMock(side_effect=Exception("no such user"))
    service.register_channel("telegram", adapter)

    with pytest.raises(HTTPException) as exc:
        await service.send_message(
            contact_id=10, channel="telegram", content="Hi", recipient="@ghost"
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_send_reply_with_recipient_overrides_contact_address(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    original = MagicMock(id=1, channel="telegram", contact_id=10, channel_message_id=None)
    service.message_repo.get_by_id = AsyncMock(return_value=original)
    service.contact_repo.get_by_id = AsyncMock(
        return_value=MagicMock(id=10, telegram_id="12345", email=None)
    )
    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_1"}
    service.register_channel("telegram", adapter)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=201))
    service.contact_repo.update = AsyncMock()

    fake_outbox = MagicMock()
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=998))
    fake_outbox.attempt_delivery = AsyncMock(return_value={"message_id": "sent_1"})
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    result = await service.send_reply(1, "Hello back", recipient="777000")

    assert result.id == 201
    assert fake_outbox.enqueue.call_args.kwargs["channel_id"] == "777000"


@pytest.mark.asyncio
async def test_process_incoming_updates_telegram_id(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=101))

    await service.process_incoming({
        "channel": "telegram",
        "contact_id": "tg_123",
        "message_id": "msg_2",
        "content": "Hi",
    })

    service.contact_repo.update.assert_awaited_once_with(10, telegram_id="tg_123")


@pytest.mark.asyncio
async def test_process_incoming_skips_spam_contact(service):
    contact = MagicMock(id=10, telegram_id=None, email=None, folder_id=None, life_sphere="spam")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_spam_1",
        "content": "Купите слона",
        "contact_name": "Spammer",
    })

    assert result is None
    service.message_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_skips_sphere_spam(service):
    contact = MagicMock(id=11, telegram_id=None, email=None, is_spam=False, life_sphere="spam")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock()

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_spam_2",
        "content": "Купите слона",
        "contact_name": "Spammer",
    })

    assert result is None
    service.message_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_saves_unknown_contact(service):
    contact = MagicMock(id=12, telegram_id=None, email=None, folder_id=None, is_spam=False, life_sphere="personal")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=103))

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "new_123",
        "message_id": "msg_new_1",
        "content": "Hello",
        "contact_name": "New Contact",
    })

    assert result is not None
    service.message_service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_incoming_allows_spam_when_forced(service):
    contact = MagicMock(id=13, telegram_id=None, email=None, folder_id=None, life_sphere="spam")
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=104))

    result = await service.process_incoming(
        {
            "channel": "telegram",
            "contact_id": "12345",
            "message_id": "msg_spam_force_1",
            "content": "Купите слона",
            "contact_name": "Spammer",
        },
        allow_spam=True,
    )

    assert result is not None
    service.message_service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_incoming_skips_spam_contact_integration():
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import MessageModel

    async with AsyncSessionLocal() as session:
        service = ChannelMessageService(session)
        await service.contact_repo.create(
            name="Spammer", life_sphere="spam", telegram_id="12345"
        )
        result = await service.process_incoming({
            "channel": "telegram",
            "contact_id": "12345",
            "message_id": "m_spam_int",
            "content": "spam message",
            "contact_name": "Spammer",
        })
        await session.commit()
        assert result is None

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(MessageModel.id)))
    assert count == 0


@pytest.mark.asyncio
async def test_process_incoming_skips_channel_contact_integration():
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import MessageModel

    async with AsyncSessionLocal() as session:
        service = ChannelMessageService(session)

        await service.contact_repo.create(
            name="Channel", life_sphere="channels", telegram_id="12345",
        )
        result = await service.process_incoming({
            "channel": "telegram",
            "contact_id": "12345",
            "message_id": "m_channel_int",
            "content": "channel message",
            "contact_name": "Channel",
        })
        await session.commit()
        assert result is None

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(MessageModel.id)))
    assert count == 0


@pytest.mark.asyncio
async def test_process_incoming_allows_channel_when_forced_integration():
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import MessageModel

    async with AsyncSessionLocal() as session:
        service = ChannelMessageService(session)

        await service.contact_repo.create(
            name="Channel", life_sphere="channels", telegram_id="12345",
        )
        result = await service.process_incoming(
            {
                "channel": "telegram",
                "contact_id": "12345",
                "message_id": "m_channel_forced",
                "content": "channel message",
                "contact_name": "Channel",
            },
            allow_channels=True,
        )
        await session.commit()
        assert result is not None

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(MessageModel.id)))
    assert count == 1


@pytest.mark.asyncio
async def test_process_incoming_rolls_back_contact_on_message_failure(monkeypatch):
    """R1-14: сбой message_service.create — контакт и сообщение откатываются."""
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import ContactModel, MessageModel

    async with AsyncSessionLocal() as session:
        service = ChannelMessageService(session)

        async def _fail_create(*args, **kwargs):
            raise RuntimeError("injected message creation failure")

        monkeypatch.setattr(service.message_service, "create", _fail_create)

        with pytest.raises(RuntimeError):
            await service.process_incoming({
                "channel": "telegram",
                "contact_id": "12345",
                "message_id": "msg_rollback_1",
                "content": "Hello World",
                "contact_name": "Rollback Contact",
            })

        await session.rollback()

    async with AsyncSessionLocal() as session:
        contacts = await session.scalar(select(func.count(ContactModel.id)))
        messages = await session.scalar(select(func.count(MessageModel.id)))
    assert contacts == 0, f"должно быть 0 контактов после отката, есть {contacts}"
    assert messages == 0, f"должно быть 0 сообщений после отката, есть {messages}"

@pytest.mark.asyncio
async def test_process_incoming_skips_blocked_contact(service):
    contact = MagicMock(
        id=10,
        telegram_id=None,
        email=None,
        folder_id=None,
        is_spam=False,
        life_sphere="personal",
        is_blocked=True,
    )
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.message_repo.get_by_channel_message = AsyncMock(return_value=None)
    service.message_service.create = AsyncMock(return_value=MagicMock(id=100))

    result = await service.process_incoming({
        "channel": "telegram",
        "contact_id": "12345",
        "message_id": "msg_blocked",
        "content": "Hello",
        "contact_name": "John",
    })

    assert result is None
    service.message_service.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_to_recipient_success(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    adapter = AsyncMock()
    adapter.resolve_channel_id = AsyncMock(return_value="channel_id_1")
    adapter.send_message.return_value = {"message_id": "sent_new_1"}
    service.register_channel("email", adapter)

    contact = MagicMock(id=30)
    service.contact_repo.get_or_create = AsyncMock(return_value=contact)
    service.contact_repo.update = AsyncMock()
    service.message_service.create = AsyncMock(return_value=MagicMock(id=300))
    service.message_repo.update = AsyncMock()
    service.message_repo.get_by_id = AsyncMock(return_value=None)

    fake_outbox = MagicMock()
    fake_outbox.get_by_client_request_id = AsyncMock(return_value=None)
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=998))
    fake_outbox.attempt_delivery = AsyncMock(return_value={"message_id": "sent_new_1"})
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    result = await service.send_to_recipient("email", "alice@example.com", "Hi Alice")

    assert result.id == 300
    adapter.resolve_channel_id.assert_awaited_once_with("alice@example.com")
    service.contact_repo.get_or_create.assert_awaited_once_with(
        name="alice@example.com", channel="email", channel_id="channel_id_1"
    )
    fake_outbox.enqueue.assert_awaited_once()
    fake_outbox.attempt_delivery.assert_awaited_once()
    service.contact_repo.update.assert_awaited_once_with(30, is_known=True)


@pytest.mark.asyncio
async def test_send_to_recipient_strips_at_sign(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    adapter = AsyncMock()
    adapter.resolve_channel_id = AsyncMock(return_value="12345")
    adapter.send_message.return_value = {"message_id": "sent_tg_1"}
    service.register_channel("telegram", adapter)

    service.contact_repo.get_or_create = AsyncMock(return_value=MagicMock(id=31))
    service.contact_repo.update = AsyncMock()
    service.message_service.create = AsyncMock(return_value=MagicMock(id=301))
    service.message_repo.update = AsyncMock()
    service.message_repo.get_by_id = AsyncMock(return_value=None)

    fake_outbox = MagicMock()
    fake_outbox.get_by_client_request_id = AsyncMock(return_value=None)
    fake_outbox.enqueue = AsyncMock(return_value=MagicMock(id=997))
    fake_outbox.attempt_delivery = AsyncMock(return_value={"message_id": "sent_tg_1"})
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    await service.send_to_recipient("telegram", "@alice", "Hi")

    adapter.resolve_channel_id.assert_awaited_once_with("alice")
    service.contact_repo.get_or_create.assert_awaited_once_with(
        name="alice", channel="telegram", channel_id="12345"
    )


@pytest.mark.asyncio
async def test_send_to_recipient_no_adapter_raises_503(service):
    with pytest.raises(HTTPException) as exc:
        await service.send_to_recipient("telegram", "alice", "Hi")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_send_to_recipient_empty_recipient_raises_400(service):
    adapter = AsyncMock()
    service.register_channel("email", adapter)
    with pytest.raises(HTTPException) as exc:
        await service.send_to_recipient("email", "  ", "Hi")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_send_to_recipient_client_request_id_dedup(service, monkeypatch):
    from app.services import channel_message_service as cms_mod

    adapter = AsyncMock()
    adapter.resolve_channel_id = AsyncMock(return_value="abc")
    service.register_channel("email", adapter)

    existing = MagicMock(message_id=400)
    fake_outbox = MagicMock()
    fake_outbox.repo = MagicMock()
    fake_outbox.repo.get_by_client_request_id = AsyncMock(return_value=existing)
    monkeypatch.setattr(cms_mod, "OutboxService", lambda *a, **k: fake_outbox)

    service.contact_repo.get_or_create = AsyncMock(return_value=MagicMock(id=40))
    service.message_repo.get_by_id = AsyncMock(
        return_value=MessageResponse(
            id=400,
            contact_id=40,
            channel="email",
            content="Hi",
            direction="outgoing",
            status="read",
        )
    )
    result = await service.send_to_recipient("email", "a@b.c", "Hi", client_request_id="req-1")

    assert result.id == 400
    fake_outbox.enqueue.assert_not_called()
