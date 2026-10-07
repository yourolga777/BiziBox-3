import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pyrogram import Client  # type: ignore[attr-defined]
from pyrogram.raw.types.auth import SentCodeTypeSms  # type: ignore[attr-defined]

from ...channels.telegram import TelegramAdapter
from ...config import settings
from ...database import get_async_session_maker
from ...deps import get_poll_service
from ...models.channel import ChannelModel
from ...services.settings_service import get_poll_interval

logger = logging.getLogger(__name__)


@dataclass
class _PendingAuth:
    client: Client
    phone: str
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


_pending_auths: dict[int, _PendingAuth] = {}
_cleanup_task: asyncio.Task[Any] | None = None

# Минимальная пауза между отправками кода для одного канала. Каждый новый
# send_code от Telegram инвалидирует предыдущий in-app код; частые повторные
# запросы (флуд) заставляют Telegram троттлить доставку на номер.
_CODE_COOLDOWN_SECONDS = 60
_last_code_sent_at: dict[int, datetime] = {}


@dataclass
class _CodeSendResult:
    code_type: str
    next_type: str | None
    timeout: int | None
    phone_registered: bool | None


def _parse_sent_code(sent: Any) -> _CodeSendResult:
    """Извлечь из SentCode тип доставки, следующий канал и таймаут.

    code_type: как ушёл код сейчас (app/sms/call/...).
    next_type: каким способом TG доставит код при повторной отправке
               (resend_code использует именно следующий тип).
    timeout: через сколько секунд TG разрешит следующий запрос.
    """
    raw = getattr(sent, "_raw", None)
    if raw is None:
        return _CodeSendResult(code_type="app", next_type=None,
                               timeout=None, phone_registered=None)

    if isinstance(raw.type, SentCodeTypeSms):
        code_type = "sms"
    elif "Call" in raw.type.__class__.__name__:
        code_type = "call"
    else:
        code_type = "app"

    next_type: str | None = None
    if raw.next_type is not None:
        next_type = raw.next_type.__class__.__name__.replace("CodeType", "").lower()

    timeout: int | None = int(raw.timeout) if raw.timeout else None
    phone_registered: bool | None = bool(raw.phone_registered)

    return _CodeSendResult(
        code_type=code_type,
        next_type=next_type,
        timeout=timeout,
        phone_registered=phone_registered,
    )


def _mark_code_sent(channel_id: int) -> None:
    _last_code_sent_at[channel_id] = datetime.now()


def _code_cooldown_remaining(channel_id: int) -> int:
    last = _last_code_sent_at.get(channel_id)
    if not last:
        return 0
    elapsed = (datetime.now() - last).total_seconds()
    return max(int(_CODE_COOLDOWN_SECONDS - elapsed), 0)


async def _cleanup_stale_auths() -> None:
    while True:
        try:
            await asyncio.sleep(60)
            now = datetime.now()
            stale = [
                cid for cid, auth in list(_pending_auths.items())
                if now - auth.created_at > timedelta(minutes=10)
            ]
            for cid in stale:
                auth = _pending_auths.pop(cid, None)
                if auth:
                    try:
                        await auth.client.disconnect()
                        logger.info("Cleaned up stale pending auth for channel %s", cid)
                    except Exception:
                        logger.warning(
                            "Failed to disconnect stale client for channel %s", cid,
                        )
            now = datetime.now()
            stale_cooldown = [
                cid for cid, ts in list(_last_code_sent_at.items())
                if (now - ts).total_seconds() > _CODE_COOLDOWN_SECONDS
            ]
            for cid in stale_cooldown:
                _last_code_sent_at.pop(cid, None)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Pending auth cleanup error")


def _ensure_cleanup() -> asyncio.Task[Any]:
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(_cleanup_stale_auths())
    return _cleanup_task


async def cleanup_pending_auths() -> None:
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
    for cid, auth in list(_pending_auths.items()):
        del _pending_auths[cid]
        try:
            await auth.client.disconnect()
        except Exception:
            pass


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


async def _send_code_via(
    client: Client,
    phone: str,
    via: str,
) -> Any:
    """Send verification code, logging the requested delivery method.

    Pyrogram 2.0.106 removed ``force_sms`` from ``CodeSettings``, so we
    cannot force SMS through the raw API.  We log the *requested* method
    and the *actual* type + next_type + timeout returned by Telegram so
    that delivery issues can be traced and cooldowns respected.
    """
    logger.info(
        "send_code requested via=%s for phone=%s", via, phone,
    )
    result = await client.send_code(phone)
    info = _parse_sent_code(result)
    logger.info(
        "send_code completed: type=%s next_type=%s timeout=%s "
        "phone_registered=%s (requested via=%s) phone=%s",
        info.code_type, info.next_type, info.timeout,
        info.phone_registered, via, phone,
    )
    return result


async def _handle_code_expired(
    pending: _PendingAuth,
    channel: ChannelModel,
    old_phone_code_hash: str,
) -> dict[str, Any]:
    if pending.retry_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Код подтверждения истёк. Начните заново — нажмите «Получить код»",
        )

    await asyncio.sleep(1)
    try:
        result = await pending.client.resend_code(pending.phone, old_phone_code_hash)
    except Exception as e:
        logger.error(f"Auto-resend error after expired code: {e}")
        raise HTTPException(
            status_code=400,
            detail="Код подтверждения истёк. Запросите новый код вручную.",
        )

    _mark_code_sent(int(channel.id))
    pending.retry_count += 1
    attempt = pending.retry_count + 1

    return {
        "status": "code_expired",
        "channel_id": channel.id,
        "phone_code_hash": result.phone_code_hash,
        "retry_count": pending.retry_count,
        "message": f"Код истёк. Новый код отправлен (попытка {attempt}/3)",
    }


async def _init_telegram_adapter(
    phone: str,
    session_string: str,
    api_id: Any,
    api_hash: str,
    proxy: Any,
) -> None:
    ps = get_poll_service()
    if not ps:
        logger.warning("poll_service is None, cannot register Telegram adapter")
        return

    tg_adapter = TelegramAdapter()
    connected = await tg_adapter.connect(config={
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone,
        "session_string": session_string,
        "session_name": f"bizibox_{phone}",
        "session_dir": "./data/sessions",
        "proxy": proxy,
    })
    if not connected:
        logger.error("Failed to connect Telegram adapter in background task")
        return

    ps.register_channel("telegram", tg_adapter)
    interval = settings.TELEGRAM_POLL_INTERVAL
    try:
        session_maker = get_async_session_maker()
        async with session_maker() as sess:
            interval = await get_poll_interval(
                sess, "telegram_poll_interval", settings.TELEGRAM_POLL_INTERVAL,
            )
    except Exception:
        logger.warning("Could not load DB poll interval, using default", exc_info=True)
    ps.start("telegram", interval)
    logger.info("Telegram adapter initialized and poll started (background task)")
