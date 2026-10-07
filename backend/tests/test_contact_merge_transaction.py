import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import ContactModel, MessageModel
from app.services.contact_service import ContactService


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_merge_rolls_back_on_http_exception(monkeypatch):
    """R1-14: HTTPException(400) при merge — откат всех шагов."""
    async with AsyncSessionLocal() as session:
        service = ContactService(session)
        primary = await service.contact_repo.create(
            name="PrimaryHTTP", phone="+111"
        )
        secondary = await service.contact_repo.create(
            name="SecondaryHTTP", phone="+222"
        )
        pid = int(primary.id)
        sid = int(secondary.id)

        await service.session.execute(
            MessageModel.__table__.insert().values(  # type: ignore[attr-defined]
                contact_id=sid,
                channel="telegram",
                channel_message_id="msg_http_1",
                content="test",
                direction="incoming",
                status="unread",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        service = ContactService(session)

        async def _fail_http(*args, **kwargs):
            raise HTTPException(status_code=400, detail="injected HTTP failure")

        monkeypatch.setattr(service, "_transfer_messages", _fail_http)

        with pytest.raises(HTTPException) as exc:
            await service.merge(primary_id=pid, secondary_id=sid)
        assert exc.value.status_code == 400

        await session.rollback()

    async with AsyncSessionLocal() as session:
        secondary_after = await session.get(ContactModel, sid)
        assert secondary_after is not None
        assert secondary_after.deleted_at is None, "secondary не должен быть удалён"

        primary_after = await session.get(ContactModel, pid)
        assert primary_after is not None
        assert primary_after.deleted_at is None

        messages = list(
            (await session.execute(
                select(MessageModel).where(MessageModel.contact_id == sid)
            )).scalars()
        )
        assert len(messages) == 1, "сообщение должно остаться у secondary после отката"
