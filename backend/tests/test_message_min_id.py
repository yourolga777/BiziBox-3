import pytest

from app.repositories import ContactRepository, MessageRepository
from app.services.message_service import MessageService


async def _seed(db_session, contact_repo, msg_repo, count=5):
    contact = await contact_repo.create(name="Seed")
    ids = []
    for i in range(count):
        msg = await msg_repo.create(
            contact_id=contact.id,
            channel="telegram",
            content=f"msg-{i}",
            direction="incoming",
            status="unread",
        )
        ids.append(msg.id)
    await db_session.commit()
    return contact, ids


@pytest.mark.asyncio
async def test_get_all_min_id_filters_old(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)
    _, ids = await _seed(db_session, contact_repo, msg_repo, count=5)

    after_first = await msg_repo.get_all(min_id=ids[0])
    assert all(m.id > ids[0] for m in after_first)
    assert len(after_first) == 4


@pytest.mark.asyncio
async def test_get_all_min_id_none_returns_all(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)
    _, ids = await _seed(db_session, contact_repo, msg_repo, count=3)

    all_msgs = await msg_repo.get_all()
    assert len(all_msgs) == 3
    assert set(m.id for m in all_msgs) == set(ids)


@pytest.mark.asyncio
async def test_get_by_scope_min_id_filters(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)
    _, ids = await _seed(db_session, contact_repo, msg_repo, count=4)

    inbox = await msg_repo.get_by_scope("inbox", min_id=ids[1])
    assert len(inbox) == 2
    assert all(m.id > ids[1] for m in inbox)


@pytest.mark.asyncio
async def test_service_get_all_passes_min_id(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)
    _, ids = await _seed(db_session, contact_repo, msg_repo, count=4)

    service = MessageService(db_session)
    result = await service.get_all(min_id=ids[2])
    assert len(result) == 1
    assert result[0].id > ids[2]


@pytest.mark.asyncio
async def test_get_by_scope_inbox_includes_non_spam_excludes_spam(db_session):
    contact_repo = ContactRepository(db_session)
    msg_repo = MessageRepository(db_session)

    email_contact = await contact_repo.create(name="Email", email="a@example.com")
    spam_contact = await contact_repo.create(name="Spam", email="spam@example.com", life_sphere="spam")
    channel_contact = await contact_repo.create(name="Channel")

    await msg_repo.create(contact_id=email_contact.id, channel="email", content="e", direction="incoming")
    await msg_repo.create(contact_id=spam_contact.id, channel="email", content="s", direction="incoming")
    await msg_repo.create(contact_id=channel_contact.id, channel="telegram", content="c", direction="incoming")
    await db_session.commit()

    inbox = await msg_repo.get_by_scope("inbox")
    inbox_ids = {m.contact_id for m in inbox}
    assert email_contact.id in inbox_ids
    assert channel_contact.id in inbox_ids
    assert spam_contact.id not in inbox_ids
