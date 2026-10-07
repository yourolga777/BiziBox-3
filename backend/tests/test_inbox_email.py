import pytest

from app.repositories import ContactRepository, MessageRepository
from app.services.message_service import MessageService


async def _seed_email_message(db_session, msg_repo, content="Письмо с почты"):
    contact = await ContactRepository(db_session).create(
        name="mail@example.ru",
        email="mail@example.ru",
    )
    msg = await msg_repo.create(
        contact_id=contact.id,
        channel="email",
        content=content,
        direction="incoming",
        status="unread",
    )
    await db_session.commit()
    return contact, msg


@pytest.mark.asyncio
async def test_email_messages_appear_in_inbox(db_session):
    msg_repo = MessageRepository(db_session)
    contact, msg = await _seed_email_message(db_session, msg_repo)

    inbox = await msg_repo.get_by_scope("inbox")
    assert any(m.id == msg.id for m in inbox)


@pytest.mark.asyncio
async def test_email_messages_visible_in_service_inbox(db_session):
    msg_repo = MessageRepository(db_session)
    contact, msg = await _seed_email_message(db_session, msg_repo)

    service = MessageService(db_session)
    result = await service.get_by_scope("inbox")
    assert any(m.id == msg.id for m in result)
