from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.models import MessageModel
from app.repositories.contact import ContactRepository
from app.repositories.message import MessageRepository
from app.repositories.outbox import OutboxRepository
from app.services.channel_message_service import ChannelMessageService
from app.services.outbox_service import OutboxService


@pytest.mark.asyncio
async def test_enqueue_creates_pending(db_session):
    svc = OutboxService(db_session, owner_id=1)
    record = await svc.enqueue(
        message_id=None, channel="telegram", channel_id="123", reply_to=None, content="hi"
    )
    assert record.status == "pending"
    assert record.attempts == 0
    assert record.next_retry_at is None


@pytest.mark.asyncio
async def test_attempt_delivery_success_marks_sent(db_session):
    svc = OutboxService(db_session, owner_id=1)
    record = await svc.enqueue(
        message_id=None, channel="telegram", channel_id="123", reply_to=None, content="hi"
    )
    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_1"}

    result = await svc.attempt_delivery(adapter, record, max_attempts=5, base_delay=5)

    assert result == {"message_id": "sent_1"}
    reloaded = await svc.repo.get_by_id(int(record.id))
    assert reloaded.status == "sent"


@pytest.mark.asyncio
async def test_attempt_delivery_failure_schedules_retry(db_session):
    svc = OutboxService(db_session, owner_id=1)
    record = await svc.enqueue(
        message_id=None, channel="telegram", channel_id="123", reply_to=None, content="hi"
    )
    adapter = AsyncMock()
    adapter.send_message.side_effect = Exception("network down")

    result = await svc.attempt_delivery(adapter, record, max_attempts=5, base_delay=5)

    assert result is None
    reloaded = await svc.repo.get_by_id(int(record.id))
    assert reloaded.status == "pending"
    assert reloaded.attempts == 1
    assert reloaded.next_retry_at is not None


@pytest.mark.asyncio
async def test_attempt_delivery_exhausts_to_failed(db_session):
    svc = OutboxService(db_session, owner_id=1)
    record = await svc.enqueue(
        message_id=None, channel="telegram", channel_id="123", reply_to=None, content="hi"
    )
    adapter = AsyncMock()
    adapter.send_message.side_effect = Exception("down")

    result = await svc.attempt_delivery(adapter, record, max_attempts=1, base_delay=5)

    assert result is None
    reloaded = await svc.repo.get_by_id(int(record.id))
    assert reloaded.status == "failed"
    assert reloaded.last_error


@pytest.mark.asyncio
async def test_process_pending_links_message_no_duplicate(db_session):
    contact_repo = ContactRepository(db_session)
    contact = await contact_repo.create(name="Alice")
    msg_repo = MessageRepository(db_session)
    msg = await msg_repo.create(
        contact_id=contact.id, channel="telegram", content="reply", direction="outgoing", status="read"
    )
    await db_session.commit()

    svc = OutboxService(db_session, owner_id=1)
    await svc.enqueue(
        message_id=int(msg.id), channel="telegram", channel_id="123", reply_to=None, content="reply"
    )
    await db_session.commit()

    adapter = AsyncMock()
    adapter.send_message.return_value = {"message_id": "sent_99"}
    delivered = await svc.process_pending({"telegram": adapter}, max_attempts=5, base_delay=5)
    await db_session.commit()

    assert delivered == 1
    reloaded = await msg_repo.get_by_id(int(msg.id))
    assert reloaded.channel_message_id == "sent_99"
    outgoing_count = await db_session.scalar(
        select(func.count(MessageModel.id)).where(MessageModel.direction == "outgoing")
    )
    assert outgoing_count == 1


@pytest.mark.asyncio
async def test_send_reply_queues_on_failure_then_worker_delivers(db_session):
    contact_repo = ContactRepository(db_session)
    contact = await contact_repo.create(name="Alice", telegram_id="123")
    msg_repo = MessageRepository(db_session, owner_id=1)
    incoming = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        channel_message_id="m1",
        content="hello",
        direction="incoming",
        status="unread",
    )
    await db_session.commit()

    cms = ChannelMessageService(db_session, owner_id=1)
    failing = AsyncMock()
    failing.send_message.side_effect = Exception("network down")
    cms.register_channel("telegram", failing)

    reply = await cms.send_reply(int(incoming.id), "reply text")
    await db_session.commit()

    assert reply is not None
    assert reply.channel_message_id is None

    pending = await OutboxRepository(db_session, owner_id=1).list_by_status("pending", 0, 10)
    assert len(pending) == 1
    assert pending[0].message_id == int(reply.id)

    # Сбрасываем backoff (next_retry_at в будущем) — имитируем истечение задержки.
    from datetime import datetime

    outbox_repo = OutboxRepository(db_session, owner_id=1)
    await outbox_repo.schedule_retry(int(pending[0].id), 0, datetime.now(), None)
    await db_session.commit()

    ok = AsyncMock()
    ok.send_message.return_value = {"message_id": "sent_42"}
    svc = OutboxService(db_session, owner_id=1)
    delivered = await svc.process_pending({"telegram": ok}, max_attempts=5, base_delay=5)
    await db_session.commit()

    assert delivered == 1
    reloaded = await msg_repo.get_by_id(int(reply.id))
    assert reloaded.channel_message_id == "sent_42"
    outgoing_count = await db_session.scalar(
        select(func.count(MessageModel.id)).where(MessageModel.direction == "outgoing")
    )
    assert outgoing_count == 1
