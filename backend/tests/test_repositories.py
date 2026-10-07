from datetime import datetime, timedelta

import pytest

from app.repositories import (
    ChannelRepository,
    ContactRepository,
    MessageRepository,
    TaskRepository,
    UserRepository,
)


@pytest.mark.asyncio
async def test_contact_repository_crud(db_session):
    repo = ContactRepository(db_session)
    contact = await repo.create(name="Test", phone="+123")
    assert contact.id is not None
    assert contact.name == "Test"

    found = await repo.get_by_id(int(contact.id))
    assert found is not None
    assert found.phone == "+123"

    updated = await repo.update(int(contact.id), name="Updated")
    assert updated is not None
    assert updated.name == "Updated"

    deleted = await repo.delete(int(contact.id))
    assert deleted is True

    not_found = await repo.get_by_id(int(contact.id))
    assert not_found is None


@pytest.mark.asyncio
async def test_contact_search(db_session):
    repo = ContactRepository(db_session)
    await repo.create(name="Иван Петров", phone="+79161234567")
    await repo.create(name="Петр Иванов", phone="+79169876543")

    results = await repo.search("Петров")
    assert len(results) == 1

    results = await repo.search("+7916123")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_contact_by_telegram(db_session):
    repo = ContactRepository(db_session)
    await repo.create(name="Telegram User", telegram_id="tg_123")

    found = await repo.get_by_telegram_id("tg_123")
    assert found is not None
    assert found.name == "Telegram User"

    not_found = await repo.get_by_telegram_id("tg_nonexistent")
    assert not_found is None


@pytest.mark.asyncio
async def test_get_or_create_telegram_saves_username(db_session):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(
        name="John",
        channel="telegram",
        channel_id="tg_456",
        telegram_username="johnny",
    )
    assert contact.telegram_id == "tg_456"
    assert contact.telegram_username == "johnny"


@pytest.mark.asyncio
async def test_get_or_create_telegram_updates_username(db_session):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(
        name="John",
        channel="telegram",
        channel_id="tg_789",
        telegram_username="old_name",
    )
    assert contact.telegram_username == "old_name"

    updated = await repo.get_or_create(
        name="John",
        channel="telegram",
        channel_id="tg_789",
        telegram_username="new_name",
    )
    assert updated.id == contact.id
    assert updated.telegram_username == "new_name"


@pytest.mark.asyncio
async def test_get_or_create_telegram_keeps_username_on_none(db_session):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(
        name="John",
        channel="telegram",
        channel_id="tg_111",
        telegram_username="keeper",
    )
    assert contact.telegram_username == "keeper"

    refreshed = await repo.get_or_create(
        name="John",
        channel="telegram",
        channel_id="tg_111",
        telegram_username=None,
    )
    assert refreshed.id == contact.id
    assert refreshed.telegram_username == "keeper"


@pytest.mark.asyncio
async def test_message_repository(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    contact = await contact_repo.create(name="Test")
    msg = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        content="Hello",
        direction="incoming",
        status="unread",
    )
    assert msg.id is not None

    unread = await msg_repo.get_unread()
    assert len(unread) == 1

    by_contact = await msg_repo.get_by_contact(int(contact.id))
    assert len(by_contact) == 1

    by_channel = await msg_repo.get_by_channel("telegram")
    assert len(by_channel) == 1

    by_channel_empty = await msg_repo.get_by_channel("email")
    assert len(by_channel_empty) == 0


@pytest.mark.asyncio
async def test_get_by_contact_orders_by_created_at(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    contact = await contact_repo.create(name="Merge")
    base = datetime(2026, 7, 3, 9, 42, 25)

    # Вставляем вразнобой: свежее сообщение раньше (меньший id),
    # старое (июль) позже (больший id) — как при «Загрузить ещё».
    sept = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        channel_message_id="tg_sept",
        content="new",
        direction="incoming",
        status="unread",
        created_at=base + timedelta(days=74),
    )
    july = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        channel_message_id="tg_july",
        content="old",
        direction="incoming",
        status="read",
        created_at=base,
    )
    assert july.id > sept.id

    dialog = await msg_repo.get_by_contact(int(contact.id))
    assert [int(m.id) for m in dialog] == [int(sept.id), int(july.id)]

    oldest = await msg_repo.get_oldest_by_contact(int(contact.id))
    assert oldest is not None and oldest.id == july.id

    # Курсор: следующая страница после самого свежего сообщения.
    page = await msg_repo.get_by_contact(
        int(contact.id),
        limit=1,
        before_created_at=sept.created_at,
        before_id=int(sept.id),
    )
    assert [int(m.id) for m in page] == [int(july.id)]


@pytest.mark.asyncio
async def test_get_by_contact_tiebreak_by_id(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    contact = await contact_repo.create(name="Tie")
    ts = datetime(2026, 9, 1, 20, 7, 5)

    first = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        channel_message_id="tg_a",
        content="a",
        direction="incoming",
        status="read",
        created_at=ts,
    )
    second = await msg_repo.create(
        contact_id=contact.id,
        channel="telegram",
        channel_message_id="tg_b",
        content="b",
        direction="incoming",
        status="read",
        created_at=ts,
    )

    dialog = await msg_repo.get_by_contact(int(contact.id))
    assert [int(m.id) for m in dialog] == [int(second.id), int(first.id)]


@pytest.mark.asyncio
async def test_get_latest_by_contact_returns_latest_per_contact(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    friends = await contact_repo.create(name="Old Friend", life_sphere="personal")
    active = await contact_repo.create(name="Active")
    spam = await contact_repo.create(name="Spam", life_sphere="spam")

    # У «друга» последнее сообщение старое — должен всё равно попасть в список.
    base = datetime(2026, 7, 1, 12, 0, 0)
    await msg_repo.create(
        contact_id=friends.id, channel="telegram", channel_message_id="f1",
        content="old1", direction="incoming", status="read", created_at=base,
    )
    await msg_repo.create(
        contact_id=friends.id, channel="telegram", channel_message_id="f2",
        content="old2", direction="incoming", status="unread",
        created_at=base + timedelta(days=1),
    )

    new_ts = datetime(2026, 9, 15, 10, 0, 0)
    await msg_repo.create(
        contact_id=active.id, channel="email", channel_message_id="a1",
        content="new1", direction="incoming", status="unread", created_at=new_ts,
    )
    await msg_repo.create(
        contact_id=spam.id, channel="telegram", channel_message_id="s1",
        content="spam1", direction="incoming", status="unread",
        created_at=new_ts + timedelta(days=1),
    )

    latest = await msg_repo.get_latest_by_contact()
    by_contact = {int(m.contact_id): m for m in latest}
    assert friends.id in by_contact
    assert active.id in by_contact
    assert spam.id not in by_contact
    assert len(latest) == 2

    assert by_contact[int(friends.id)].channel_message_id == "f2"

    unread = await msg_repo.get_unread_counts([int(friends.id), int(active.id)])
    assert unread[int(friends.id)] == 1
    assert unread[int(active.id)] == 1

    channels = await msg_repo.get_channels_by_contact(
        [int(friends.id), int(active.id)]
    )
    assert channels[int(friends.id)] == ["telegram"]
    assert channels[int(active.id)] == ["email"]


@pytest.mark.asyncio
async def test_get_threads_assembles_thread_response(db_session):
    from app.services.message_service import MessageService

    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    contact = await contact_repo.create(name="Threaded", life_sphere="work")
    await msg_repo.create(
        contact_id=contact.id, channel="telegram", channel_message_id="t1",
        content="hello", direction="incoming", status="unread",
        created_at=datetime(2026, 9, 16, 10, 0, 0),
    )

    service = MessageService(db_session)
    threads = await service.get_threads()
    assert len(threads) == 1
    thread = threads[0]
    assert thread.contact_id == int(contact.id)
    assert thread.last_message.channel_message_id == "t1"
    assert thread.last_message.contact_name == "Threaded"
    assert thread.unread_count == 1
    assert thread.channels == ["telegram"]


@pytest.mark.asyncio
async def test_mark_contact_read_marks_whole_contact(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    contact_a = await contact_repo.create(name="A")
    contact_b = await contact_repo.create(name="B")

    await msg_repo.create(
        contact_id=contact_a.id, channel="telegram", channel_message_id="a1",
        content="x", direction="incoming", status="unread",
        created_at=datetime(2026, 9, 1, 10, 0, 0),
    )
    await msg_repo.create(
        contact_id=contact_a.id, channel="telegram", channel_message_id="a2",
        content="y", direction="incoming", status="read",
        created_at=datetime(2026, 9, 2, 10, 0, 0),
    )
    deleted = await msg_repo.create(
        contact_id=contact_a.id, channel="telegram", channel_message_id="a3",
        content="z", direction="incoming", status="unread",
        created_at=datetime(2026, 9, 3, 10, 0, 0),
    )
    await msg_repo.bulk_soft_delete([int(deleted.id)])

    await msg_repo.create(
        contact_id=contact_b.id, channel="email", channel_message_id="b1",
        content="other", direction="incoming", status="unread",
        created_at=datetime(2026, 9, 4, 10, 0, 0),
    )

    updated = await msg_repo.mark_contact_read(int(contact_a.id))
    assert updated == 1

    a_messages = await msg_repo.get_all(contact_id=int(contact_a.id), limit=100)
    statuses = {m.channel_message_id: m.status for m in a_messages}
    assert statuses["a1"] == "read"
    assert statuses["a2"] == "read"

    b_messages = await msg_repo.get_all(contact_id=int(contact_b.id), limit=100)
    assert b_messages[0].status == "unread"


@pytest.mark.asyncio
async def test_task_repository(db_session):
    contact_repo = ContactRepository(db_session)
    task_repo = TaskRepository(db_session)

    contact = await contact_repo.create(name="Test")
    task = await task_repo.create(
        contact_id=contact.id,
        title="Test task",
        status="new",
    )
    assert task.id is not None

    pending = await task_repo.get_pending()
    assert len(pending) == 1

    by_status = await task_repo.get_by_status("completed")
    assert len(by_status) == 0


@pytest.mark.asyncio
async def test_channel_repository(db_session):
    repo = ChannelRepository(db_session)
    await repo.create(type="telegram", name="Telegram", is_connected=True)
    await repo.create(type="email", name="Email", is_connected=False)

    connected = await repo.get_connected()
    assert len(connected) == 1
    assert connected[0].type == "telegram"

    by_type = await repo.get_by_type("email")
    assert len(by_type) == 1


@pytest.mark.asyncio
async def test_user_repository(db_session):
    repo = UserRepository(db_session)
    await repo.create(username="admin", password_hash="hash1")

    user = await repo.get_by_username("admin")
    assert user is not None
    assert user.password_hash == "hash1"

    not_found = await repo.get_by_username("nobody")
    assert not_found is None
