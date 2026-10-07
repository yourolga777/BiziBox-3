import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.channels.telegram import TelegramAdapter
from app.database import init_db
from app.repositories.contact import ContactRepository
from app.schemas.message import AttachmentInput, MessageCreate
from app.services.message_service import MessageService
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_create_message_with_attachments_persists(db_session):
    contact_repo = ContactRepository(db_session)
    contact = await contact_repo.get_or_create(
        name="Test", channel="telegram", channel_id="123"
    )

    data = MessageCreate(
        contact_id=int(contact.id),
        channel="telegram",
        content="Photo with attachment",
        direction="incoming",
        attachments=[
            AttachmentInput(
                channel_message_id="msg_1",
                file_name="cat.jpg",
                file_size=1234,
                mime_type="image/jpeg",
                file_path="file-abc",
            )
        ],
    )
    service = MessageService(db_session)
    result = await service.create(data)
    await db_session.commit()

    assert len(result.attachments) == 1
    att = result.attachments[0]
    assert att.file_name == "cat.jpg"
    assert att.file_size == 1234
    assert att.mime_type == "image/jpeg"
    assert att.channel_message_id == "msg_1"

    reloaded = await service.get_by_id(result.id)
    assert reloaded is not None
    assert len(reloaded.attachments) == 1
    assert reloaded.attachments[0].file_path == "file-abc"


@pytest.mark.asyncio
async def test_create_message_without_attachments_returns_empty(db_session):
    contact_repo = ContactRepository(db_session)
    contact = await contact_repo.get_or_create(
        name="Empty", channel="telegram", channel_id="999"
    )

    data = MessageCreate(
        contact_id=int(contact.id),
        channel="telegram",
        content="no attachments",
        direction="incoming",
    )
    service = MessageService(db_session)
    result = await service.create(data)
    await db_session.commit()

    assert result.attachments == []


@pytest.mark.asyncio
async def test_download_attachment_endpoint():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "Download Test"})
        cid = c.json()["id"]
        m = await client.post("/api/messages/", json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "Inbox doc",
            "direction": "incoming",
            "attachments": [{
                "channel_message_id": "msg_doc",
                "file_name": "report.pdf",
                "file_size": 2048,
                "mime_type": "application/pdf",
                "file_path": "tg-file-123",
            }],
        })
        assert m.status_code == 201
        msg = m.json()
        assert len(msg["attachments"]) == 1
        att = msg["attachments"][0]

        adapter = AsyncMock()
        adapter.download_file = AsyncMock(return_value=io.BytesIO(b"%PDF-1.4 fake"))
        ps = MagicMock()
        ps.get_channel.return_value = adapter

        with patch("app.routers.messages.get_poll_service", return_value=ps):
            resp = await client.get(
                f"/api/messages/{msg['id']}/attachments/{att['id']}/download"
            )

        assert resp.status_code == 200
        assert resp.content == b"%PDF-1.4 fake"
        assert "inline" in resp.headers["content-disposition"]
        assert "report.pdf" in resp.headers["content-disposition"]
        assert resp.headers["accept-ranges"] == "bytes"


@pytest.mark.asyncio
async def test_download_attachment_range_partial():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "Range Test"})
        cid = c.json()["id"]
        m = await client.post("/api/messages/", json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "video",
            "direction": "incoming",
            "attachments": [{
                "channel_message_id": "msg_vid",
                "file_name": "clip.mp4",
                "file_size": 10,
                "mime_type": "video/mp4",
                "file_path": "tg-file-vid",
            }],
        })
        assert m.status_code == 201
        msg = m.json()
        att = msg["attachments"][0]

        payload = b"0123456789"
        adapter = AsyncMock()
        adapter.download_file = AsyncMock(return_value=io.BytesIO(payload))
        ps = MagicMock()
        ps.get_channel.return_value = adapter

        with patch("app.routers.messages.get_poll_service", return_value=ps):
            resp = await client.get(
                f"/api/messages/{msg['id']}/attachments/{att['id']}/download",
                headers={"range": "bytes=2-5"},
            )

        assert resp.status_code == 206
        assert resp.content == b"2345"
        assert resp.headers["content-range"] == "bytes 2-5/10"
        assert resp.headers["content-length"] == "4"


@pytest.mark.asyncio
async def test_download_attachment_range_invalid():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "Range Invalid"})
        cid = c.json()["id"]
        m = await client.post("/api/messages/", json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "video",
            "direction": "incoming",
            "attachments": [{
                "channel_message_id": "msg_vid2",
                "file_name": "clip2.mp4",
                "file_size": 10,
                "mime_type": "video/mp4",
                "file_path": "tg-file-vid2",
            }],
        })
        msg = m.json()
        att = msg["attachments"][0]

        payload = b"0123456789"
        adapter = AsyncMock()
        adapter.download_file = AsyncMock(return_value=io.BytesIO(payload))
        ps = MagicMock()
        ps.get_channel.return_value = adapter

        with patch("app.routers.messages.get_poll_service", return_value=ps):
            resp = await client.get(
                f"/api/messages/{msg['id']}/attachments/{att['id']}/download",
                headers={"range": "bytes=9999-10000"},
            )

        assert resp.status_code == 416
        assert resp.headers["content-range"] == "bytes */10"


@pytest.mark.asyncio
async def test_download_attachment_not_found():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "NF"})
        cid = c.json()["id"]
        m = await client.post("/api/messages/", json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "msg",
            "direction": "incoming",
        })
        msg = m.json()

        resp = await client.get(
            f"/api/messages/{msg['id']}/attachments/999999/download"
        )

        assert resp.status_code == 404


def test_telegram_extract_attachments():
    adapter = TelegramAdapter()

    class Photo:
        file_id = "p1"
        file_size = 100

    class Doc:
        file_id = "d1"
        file_name = "a.pdf"
        file_size = 200
        mime_type = "application/pdf"

    msg = MagicMock()
    msg.id = 42
    msg.document = Doc()
    msg.photo = Photo()
    msg.video = None
    msg.audio = None
    msg.voice = None
    msg.video_note = None
    msg.sticker = None
    msg.animation = None

    atts = adapter._extract_attachments(msg)
    assert len(atts) == 2

    doc = next(a for a in atts if a["file_path"] == "d1")
    assert doc["file_name"] == "a.pdf"
    assert doc["mime_type"] == "application/pdf"

    photo = next(a for a in atts if a["file_path"] == "p1")
    assert photo["mime_type"] == "image/jpeg"
    assert photo["file_name"].endswith(".jpg")


@pytest.mark.asyncio
async def test_telegram_media_without_caption_returns_empty_content():
    adapter = TelegramAdapter()

    class Doc:
        file_id = "d1"
        file_name = "x.pdf"
        file_size = 10
        mime_type = "application/pdf"

    msg = MagicMock()
    msg.id = 7
    msg.text = None
    msg.caption = None
    msg.document = Doc()
    msg.photo = None
    msg.video = None
    msg.audio = None
    msg.voice = None
    msg.video_note = None
    msg.sticker = None
    msg.animation = None

    assert adapter._extract_attachments(msg) == [{
        "file_path": "d1",
        "file_name": "x.pdf",
        "file_size": 10,
        "mime_type": "application/pdf",
    }]


@pytest.mark.asyncio
async def test_telegram_download_file():
    adapter = TelegramAdapter()
    adapter.client = AsyncMock()
    adapter.client.download_media = AsyncMock(return_value=io.BytesIO(b"hello"))

    result = await adapter.download_file("file-abc")

    assert result.read() == b"hello"
    adapter.client.download_media.assert_awaited_once_with("file-abc", in_memory=True)
