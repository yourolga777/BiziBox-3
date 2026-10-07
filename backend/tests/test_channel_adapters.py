from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pyrogram.enums import ChatType

from app.channels.base import ChannelFetchTimeoutError
from app.channels.email import EmailAdapter
from app.channels.telegram import TelegramAdapter, _build_proxy
from app.config import settings
from app.services.channel_message_service import ChannelMessageService
from app.utils.crypto import decrypt, encrypt
from app.utils.email_parser import extract_display_name


@pytest.fixture(autouse=True)
def _reset_proxy_settings():
    yield
    settings.TELEGRAM_PROXY_ENABLED = False
    settings.TELEGRAM_PROXY_TYPE = "socks5"
    settings.TELEGRAM_PROXY_HOST = ""
    settings.TELEGRAM_PROXY_PORT = 9050
    settings.TELEGRAM_PROXY_USERNAME = ""
    settings.TELEGRAM_PROXY_PASSWORD = ""
    settings.TELEGRAM_PROXY_SECRET = ""


@pytest.mark.asyncio
async def test_telegram_adapter_connect_failure():
    adapter = TelegramAdapter()
    result = await adapter.connect({"phone": "+123"})
    assert result is False
    assert adapter.client is None


@pytest.mark.asyncio
async def test_telegram_adapter_fetch_no_client():
    adapter = TelegramAdapter()
    messages = await adapter.fetch_messages()
    assert messages == []


@pytest.mark.asyncio
async def test_telegram_adapter_send_no_client():
    adapter = TelegramAdapter()
    with pytest.raises(Exception, match="Telegram client not connected"):
        await adapter.send_message("123", "hello")


@pytest.mark.asyncio
async def test_telegram_adapter_get_dialog_no_client():
    adapter = TelegramAdapter()
    messages = await adapter.get_dialog("123")
    assert messages == []


@pytest.mark.asyncio
async def test_build_proxy_disabled():
    settings.TELEGRAM_PROXY_ENABLED = False
    assert _build_proxy() is None


@pytest.mark.asyncio
async def test_build_proxy_enabled_no_auth():
    settings.TELEGRAM_PROXY_ENABLED = True
    settings.TELEGRAM_PROXY_TYPE = "socks5"
    settings.TELEGRAM_PROXY_HOST = "127.0.0.1"
    settings.TELEGRAM_PROXY_PORT = 1080
    settings.TELEGRAM_PROXY_USERNAME = ""
    settings.TELEGRAM_PROXY_PASSWORD = ""

    proxy = _build_proxy()
    assert proxy == {
        "scheme": "socks5",
        "hostname": "127.0.0.1",
        "port": 1080,
    }
    assert "username" not in proxy


@pytest.mark.asyncio
async def test_build_proxy_enabled_with_auth():
    settings.TELEGRAM_PROXY_ENABLED = True
    settings.TELEGRAM_PROXY_TYPE = "socks5"
    settings.TELEGRAM_PROXY_HOST = "proxy.example.com"
    settings.TELEGRAM_PROXY_PORT = 9050
    settings.TELEGRAM_PROXY_USERNAME = "user"
    settings.TELEGRAM_PROXY_PASSWORD = "pass"

    proxy = _build_proxy()
    assert proxy == {
        "scheme": "socks5",
        "hostname": "proxy.example.com",
        "port": 9050,
        "username": "user",
        "password": "pass",
    }


@pytest.mark.asyncio
async def test_build_proxy_https():
    settings.TELEGRAM_PROXY_ENABLED = True
    settings.TELEGRAM_PROXY_TYPE = "http"
    settings.TELEGRAM_PROXY_HOST = "10.0.0.1"
    settings.TELEGRAM_PROXY_PORT = 3128
    settings.TELEGRAM_PROXY_USERNAME = ""
    settings.TELEGRAM_PROXY_PASSWORD = ""

    proxy = _build_proxy()
    assert proxy is not None
    assert proxy["scheme"] == "http"
    assert proxy["hostname"] == "10.0.0.1"
    assert proxy["port"] == 3128


@pytest.mark.asyncio
async def test_build_proxy_mtproto():
    settings.TELEGRAM_PROXY_ENABLED = True
    settings.TELEGRAM_PROXY_TYPE = "mtproto"
    settings.TELEGRAM_PROXY_HOST = "superfast.30x.ru"
    settings.TELEGRAM_PROXY_PORT = 443
    settings.TELEGRAM_PROXY_SECRET = "ee" + "a" * 30

    proxy = _build_proxy()
    assert proxy is not None
    assert proxy["scheme"] == "mtproto"
    assert proxy["hostname"] == "superfast.30x.ru"
    assert proxy["port"] == 443
    assert proxy["secret"] == "ee" + "a" * 30
    assert "username" not in proxy
    assert "password" not in proxy


@pytest.mark.asyncio
async def test_build_proxy_mtproto_ignores_auth():
    settings.TELEGRAM_PROXY_ENABLED = True
    settings.TELEGRAM_PROXY_TYPE = "mtproto"
    settings.TELEGRAM_PROXY_HOST = "host"
    settings.TELEGRAM_PROXY_PORT = 443
    settings.TELEGRAM_PROXY_SECRET = "secret123"
    settings.TELEGRAM_PROXY_USERNAME = "user"
    settings.TELEGRAM_PROXY_PASSWORD = "pass"

    proxy = _build_proxy()
    assert proxy is not None
    assert proxy["secret"] == "secret123"
    assert "username" not in proxy
    assert "password" not in proxy


@pytest.mark.asyncio
async def test_email_adapter_connect_failure():
    adapter = EmailAdapter()
    result = await adapter.connect(
        {
            "email": "test@test.com",
            "password": "wrong",
            "imap_host": "bad",
            "smtp_host": "bad",
        }
    )
    assert result is False


@pytest.mark.asyncio
async def test_email_adapter_fetch_no_client():
    adapter = EmailAdapter()
    messages = await adapter.fetch_messages()
    assert messages == []


@pytest.mark.asyncio
async def test_email_adapter_send_no_client():
    adapter = EmailAdapter()
    with pytest.raises(Exception, match="SMTP client not connected"):
        await adapter.send_message("test@test.com", "hello")


@pytest.mark.asyncio
async def test_email_send_message_includes_in_reply_to_headers():
    import email

    adapter = EmailAdapter()
    adapter.config = {"email": "me@test.com"}
    adapter.smtp = MagicMock()

    await adapter.send_message("to@test.com", "Ответ", reply_to="<orig-1@test>")

    call = adapter.smtp.sendmail.call_args
    raw = call.args[2]
    msg = email.message_from_string(raw)
    assert msg["In-Reply-To"] == "<orig-1@test>"
    assert msg["References"] == "<orig-1@test>"


@pytest.mark.asyncio
async def test_email_adapter_get_dialog_no_client():
    adapter = EmailAdapter()
    messages = await adapter.get_dialog("test@test.com")
    assert messages == []


@pytest.mark.asyncio
async def test_contact_type_private():
    mock_dialog = MagicMock()
    mock_dialog.chat.type = ChatType.PRIVATE
    adapter = TelegramAdapter()
    assert adapter._get_contact_type(mock_dialog) == "user"


@pytest.mark.asyncio
async def test_contact_type_group():
    mock_dialog = MagicMock()
    mock_dialog.chat.type = ChatType.GROUP
    adapter = TelegramAdapter()
    assert adapter._get_contact_type(mock_dialog) == "group"


@pytest.mark.asyncio
async def test_contact_name_first_last():
    mock_dialog = MagicMock()
    mock_dialog.chat.first_name = "Иван"
    mock_dialog.chat.last_name = "Петров"
    mock_dialog.chat.title = None
    adapter = TelegramAdapter()
    assert adapter._get_contact_name(mock_dialog) == "Иван Петров"


@pytest.mark.asyncio
async def test_contact_name_title():
    mock_dialog = MagicMock()
    mock_dialog.chat.first_name = None
    mock_dialog.chat.last_name = None
    mock_dialog.chat.title = "Группа"
    adapter = TelegramAdapter()
    assert adapter._get_contact_name(mock_dialog) == "Группа"


def _async_gen(items):
    async def gen():
        for it in items:
            yield it

    return gen()


@pytest.mark.asyncio
@pytest.mark.parametrize("username,expected", [("alice", "alice"), (None, None)])
async def test_fetch_messages_extracts_contact_username(username, expected):
    adapter = TelegramAdapter()
    chat = MagicMock()
    chat.id = 12345
    chat.type = ChatType.PRIVATE
    chat.username = username
    chat.first_name = "Alice"
    chat.last_name = None
    chat.title = None
    dialog = MagicMock()
    dialog.chat = chat
    dialog.top_message = None
    msg = MagicMock()
    msg.text = "Hello"
    msg.outgoing = False
    msg.id = 1
    msg.date = datetime.now()
    msg.chat = chat
    msg.reply_to_message = None
    adapter.client = MagicMock()
    adapter.client.get_dialogs.return_value = _async_gen([dialog])
    adapter.client.get_chat_history.return_value = _async_gen([msg])

    result = await adapter.fetch_messages(limit=50)

    assert len(result) == 1
    assert result[0]["contact_username"] == expected


def _fake_dialog(chat, unread_count=0):
    dialog = MagicMock()
    dialog.chat = chat
    dialog.top_message = None
    dialog.unread_messages_count = unread_count
    return dialog


def _msg(id_, chat, text="Hello", outgoing=False, date=None):
    msg = MagicMock()
    msg.text = text
    msg.outgoing = outgoing
    msg.id = id_
    msg.date = date or datetime.now()
    msg.chat = chat
    msg.reply_to_message = None
    return msg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unread_count,outgoing,expected",
    [
        (0, False, "read"),  # read dialog, incoming
        (3, False, "unread"),  # unread dialog, incoming
        (3, True, "read"),  # unread dialog, but outgoing message
    ],
)
async def test_fetch_messages_status_map(unread_count, outgoing, expected):
    adapter = TelegramAdapter()
    chat = MagicMock()
    chat.id = 12345
    chat.type = ChatType.PRIVATE
    chat.username = None
    chat.first_name = "Alice"
    chat.last_name = None
    chat.title = None
    dialog = _fake_dialog(chat, unread_count)
    msg = _msg(1, chat, outgoing=outgoing)
    adapter.client = MagicMock()
    adapter.client.get_dialogs.return_value = _async_gen([dialog])
    adapter.client.get_chat_history.return_value = _async_gen([msg])

    result = await adapter.fetch_messages(limit=50)

    assert len(result) == 1
    assert result[0]["status"] == expected


@pytest.mark.asyncio
async def test_telegram_fetch_messages_timeout_raises():
    import asyncio

    async def _slow_hist(chat_id, limit=None, offset_id=None):
        await asyncio.sleep(5)
        yield _msg(1, MagicMock())

    adapter = TelegramAdapter()
    adapter.FETCH_TIMEOUT_SECONDS = 0.1
    adapter.client = MagicMock()
    adapter.client.get_dialogs.return_value = _async_gen([_fake_dialog(MagicMock())])
    adapter.client.get_chat_history.side_effect = _slow_hist

    with pytest.raises(ChannelFetchTimeoutError):
        await adapter.fetch_messages(limit=50)


@pytest.mark.asyncio
async def test_fetch_messages_catchup_since():
    from datetime import timedelta

    adapter = TelegramAdapter()
    now = datetime.now()
    recent = now - timedelta(hours=1)
    old = now - timedelta(hours=48)

    chat = MagicMock()
    chat.id = 1
    chat.type = ChatType.PRIVATE
    chat.username = None
    chat.first_name = "U"
    chat.last_name = None
    chat.title = None
    dialog = _fake_dialog(chat)
    dialog.top_message = _msg(2, chat, date=recent)

    adapter.client = MagicMock()
    adapter.client.get_dialogs.return_value = _async_gen([dialog])
    adapter.client.get_chat_history.return_value = _async_gen(
        [_msg(2, chat, date=recent), _msg(1, chat, date=old)]
    )

    since = now - timedelta(hours=24)
    result = await adapter.fetch_messages(since=since, limit=2000)

    assert [m["message_id"] for m in result] == ["2"]


@pytest.mark.asyncio
async def test_fetch_messages_first_run_24h_window():
    from datetime import timedelta

    adapter = TelegramAdapter()
    now = datetime.now()
    recent = now - timedelta(hours=1)
    old = now - timedelta(hours=48)

    chat = MagicMock()
    chat.id = 1
    chat.type = ChatType.PRIVATE
    chat.username = None
    chat.first_name = "U"
    chat.last_name = None
    chat.title = None
    dialog = _fake_dialog(chat)
    dialog.top_message = _msg(2, chat, date=recent)

    adapter.client = MagicMock()
    adapter.client.get_dialogs.return_value = _async_gen([dialog])
    adapter.client.get_chat_history.return_value = _async_gen(
        [_msg(2, chat, date=recent), _msg(1, chat, date=old)]
    )

    result = await adapter.fetch_messages(since=None, limit=2000)

    assert [m["message_id"] for m in result] == ["2"]


@pytest.mark.asyncio
async def test_email_fetch_messages_timeout_raises():
    import time

    adapter = EmailAdapter()
    adapter.FETCH_TIMEOUT_SECONDS = 0.1
    adapter.imap = MagicMock()

    def _blocking_search(*args, **kwargs):
        time.sleep(5)
        return ("OK", [b""])

    adapter.imap.search.side_effect = _blocking_search

    with pytest.raises(ChannelFetchTimeoutError):
        await adapter.fetch_messages(limit=50)


@pytest.mark.asyncio
async def test_email_fetch_messages_reconnects_on_dead_connection():
    import imaplib

    adapter = EmailAdapter()
    adapter.config = {
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "email": "a@b.com",
        "password": "secret",
    }
    adapter.imap = MagicMock()

    def _dead_search(*args, **kwargs):
        raise imaplib.IMAP4.abort("connection closed")

    adapter.imap.search.side_effect = _dead_search

    async def _fake_connect(config):
        adapter.imap = MagicMock()
        adapter.imap.search.return_value = ("OK", [b""])
        adapter.imap.status.return_value = ("OK", [b""])
        return True

    adapter.connect = _fake_connect  # type: ignore[method-assign]
    reconnect_spy = AsyncMock(wraps=adapter.reconnect)
    adapter.reconnect = reconnect_spy  # type: ignore[method-assign]

    result = await adapter.fetch_messages(limit=50)

    assert result == []
    assert reconnect_spy.call_count == 1


def test_crypto_encrypt_decrypt():
    original = "my_secret_password_123"
    encrypted = encrypt(original)
    assert encrypted != original
    decrypted = decrypt(encrypted)
    assert decrypted == original


def test_crypto_different_ciphertexts():
    text = "test"
    e1 = encrypt(text)
    e2 = encrypt(text)
    assert e1 != e2


@pytest.mark.asyncio
async def test_email_parse_date():
    adapter = EmailAdapter()
    date = adapter._parse_date("Mon, 08 Jul 2026 10:00:00 +0300")
    assert date is not None
    assert date.hour == 7  # converted to UTC
    assert date.minute == 0

    date_utc = adapter._parse_date("Mon, 08 Jul 2026 10:00:00 +0000")
    assert date_utc is not None
    assert date_utc.hour == 10

    date_no_tz = adapter._parse_date("Mon, 08 Jul 2026 10:00:00")
    assert date_no_tz is not None
    assert date_no_tz.hour == 10  # assumed UTC


@pytest.mark.asyncio
async def test_email_parse_date_none():
    adapter = EmailAdapter()
    assert adapter._parse_date(None) is None
    assert adapter._parse_date("") is None
    assert adapter._parse_date("invalid") is None


@pytest.mark.asyncio
async def test_email_extract_email():
    adapter = EmailAdapter()
    result = adapter._extract_email("Иван Петров <ivan@test.com>")
    assert result == "ivan@test.com"


@pytest.mark.asyncio
async def test_email_extract_email_plain():
    adapter = EmailAdapter()
    result = adapter._extract_email("ivan@test.com")
    assert result == "ivan@test.com"


@pytest.mark.asyncio
async def test_email_extract_body_simple():
    adapter = EmailAdapter()
    msg = MagicMock()
    msg.is_multipart.return_value = False
    msg.get_payload.return_value = b"Hello world"
    msg.get_content_charset.return_value = "utf-8"
    msg.get_content_type.return_value = "text/plain"  # Add this to fix the test

    assert adapter._extract_body(msg) == "Hello world"


@pytest.mark.asyncio
async def test_email_extract_body_multipart():
    adapter = EmailAdapter()
    part = MagicMock()
    part.get_content_type.return_value = "text/plain"
    part.get_payload.return_value = b"Body text"
    part.get_content_charset.return_value = "utf-8"

    msg = MagicMock()
    msg.is_multipart.return_value = True
    msg.walk.return_value = [msg, part]

    assert adapter._extract_body(msg) == "Body text"


@pytest.mark.asyncio
async def test_channel_message_service_register():
    service = ChannelMessageService(MagicMock())
    adapter = AsyncMock(spec=TelegramAdapter)
    adapter.channel_type = "telegram"
    service.register_channel("telegram", adapter)
    assert service.get_channel("telegram") is adapter
    assert "telegram" in service.get_all_channels()


def test_extract_display_name_from_name_and_email():
    assert extract_display_name("Ольга Исаева <olga@example.com>") == "Ольга Исаева"


def test_extract_display_name_from_email_only():
    assert extract_display_name("olga@example.com") == ""


def test_extract_display_name_from_quoted_name():
    assert extract_display_name('"Ольга Исаева" <olga@example.com>') == "Ольга Исаева"
