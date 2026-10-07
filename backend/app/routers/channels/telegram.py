import asyncio
import logging
from typing import Any

from fastapi import BackgroundTasks, Depends, HTTPException
from pyrogram import Client  # type: ignore[attr-defined]
from pyrogram.errors import (
    FloodWait,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
    Timeout,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_session
from ...repositories.channel import ChannelRepository
from ...schemas.channel import (
    ChannelConfirmTelegram,
    ChannelConnectTelegram,
    ChannelPasswordTelegram,
    ChannelResendTelegram,
)
from ...services.channel_service import ChannelService
from ...services.settings_service import get_poll_interval
from ...services.telegram_config import load_effective_telegram_config
from ...utils.crypto import decrypt, encrypt
from .auth import (
    _code_cooldown_remaining,
    _ensure_cleanup,
    _handle_code_expired,
    _init_telegram_adapter,
    _mark_code_sent,
    _normalize_phone,
    _parse_sent_code,
    _pending_auths,
    _PendingAuth,
    _send_code_via,
)
from .base import router

logger = logging.getLogger(__name__)


def _stored_2fa_password() -> str | None:
    """Возвращает сохранённый при онбординге пароль 2FA Telegram (расшифрованный)."""
    import json as _json

    from ...user_context import get_active_login, get_user_onboarding_file

    login = get_active_login()
    if not login:
        return None
    path = get_user_onboarding_file(login)
    if not path.exists():
        return None
    try:
        data = _json.loads(decrypt(path.read_text(encoding="utf-8")))
    except Exception:
        return None
    tg = data.get("telegram") or {}
    pw = tg.get("password_2fa")
    return pw if isinstance(pw, str) and pw else None


async def _check_proxy(proxy: dict[str, Any] | None) -> bool:
    """Проверить доступность прокси по его типу перед подключением.

    - socks5 — пробуем SOCKS5-рукопожатие (обнаруживает не-SOCKS порт).
    - http   — достаточно TCP-соединения.
    - mtproto — пре-чек не делаем: MTProto-прокси не отвечает на сырой
      TCP/протокольный хендшейк, его корректность проверяет Pyrogram.
    """
    if not proxy:
        return True
    scheme = str(proxy.get("scheme") or "socks5")
    host = proxy.get("hostname")
    port = proxy.get("port")
    if not host or not port:
        return True
    if scheme == "mtproto":
        return True

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(str(host), int(port)),
            timeout=5,
        )
    except (OSError, asyncio.TimeoutError) as e:
        logger.warning("_check_proxy failed: host=%s port=%s err=%s", host, port, e)
        return False

    try:
        if scheme == "socks5":
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=5)
            return resp[0] == 0x05
        return True
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as e:
        logger.warning(
            "_check_proxy handshake failed: scheme=%s host=%s port=%s err=%s",
            scheme, host, port, e,
        )
        return False
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


@router.post("/telegram/connect")
async def connect_telegram(
    data: ChannelConnectTelegram,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    phone = _normalize_phone(data.phone)
    logger.info("connect_telegram: phone=%s, via=%s", phone, data.via)

    channel_service = ChannelService(session)
    channel = await channel_service.get_or_create_telegram(phone)

    if channel.is_connected:
        raise HTTPException(status_code=400, detail="Telegram already connected")

    cooldown = _code_cooldown_remaining(int(channel.id))
    if cooldown > 0:
        raise HTTPException(
            status_code=429,
            detail=(
                "Слишком часто. Каждый новый запрос отменяет предыдущий код — "
                f"подождите {cooldown} секунд."
            ),
        )

    tg_cfg = await load_effective_telegram_config(session)
    api_id = tg_cfg["api_id"]
    api_hash = tg_cfg["api_hash"]
    proxy = tg_cfg["proxy"]

    if not api_id or not api_hash:
        raise HTTPException(
            status_code=500,
            detail="TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены. "
            "Укажите их при онбординге или в .env",
        )

    logger.info(
        "connect_telegram: proxy=%s",
        f"{proxy.get('hostname')}:{proxy.get('port')}" if proxy else "none",
    )

    if proxy is not None:
        proxy_ok = await _check_proxy(proxy)
        logger.info("connect_telegram: proxy_ok=%s", proxy_ok)
        if not proxy_ok:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Прокси Telegram не отвечает "
                    f"({proxy.get('hostname')}:{proxy.get('port')}). "
                    "Telegram поддерживает SOCKS5/HTTP/MTProto-прокси. "
                    "Если у вас VPN-приложение (v2rayN/Xray/Clash), укажите его "
                    "локальный адрес вида 127.0.0.1:порт, а не IP сервера. "
                    "Если VPN работает на уровне системы — отключите прокси "
                    "в настройках."
                ),
            )

    await session.commit()

    existing = _pending_auths.get(int(channel.id))
    if existing:
        del _pending_auths[int(channel.id)]
        try:
            await existing.client.disconnect()
        except Exception:
            pass

    client: Client | None = None
    for attempt in range(3):
        try:
            client = Client(
                name=f"bizibox_{phone}",
                api_id=api_id,
                api_hash=api_hash,
                phone_number=phone,
                in_memory=True,
                proxy=proxy,
            )
            await asyncio.wait_for(client.connect(), timeout=45)
            sent_code = await asyncio.wait_for(
                _send_code_via(client, phone, data.via),
                timeout=20,
            )

            _pending_auths[int(channel.id)] = _PendingAuth(client=client, phone=phone)
            _mark_code_sent(int(channel.id))
            _ensure_cleanup()

            info = _parse_sent_code(sent_code)
            if info.code_type == "sms":
                message = "Код отправлен по SMS"
            else:
                message = "Код отправлен в Telegram"

            return {
                "status": "code_sent",
                "channel_id": channel.id,
                "phone_code_hash": sent_code.phone_code_hash,
                "code_type": info.code_type,
                "next_type": info.next_type,
                "timeout": info.timeout or 60,
                "message": message,
            }

        except PhoneNumberInvalid:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise HTTPException(status_code=400, detail="Неверный номер телефона")

        except FloodWait as e:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise HTTPException(
                status_code=429,
                detail=f"Слишком много запросов. Подождите {e.value} секунд.",
            )

        except (Timeout, OSError, asyncio.TimeoutError) as exc:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                client = None
            if attempt < 2:
                logger.warning(
                    "connect_telegram: attempt %d failed (%s), retrying...",
                    attempt + 1, type(exc).__name__,
                )
                await asyncio.sleep(3)
                continue
            raise HTTPException(
                status_code=503,
                detail="Нет соединения с Telegram. Проверьте интернет.",
            )

        except Exception as e:
            error_str = str(e)
            if "SEND_CODE_UNAVAILABLE" in error_str:
                if client:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Код уже отправлен ранее. "
                        "Подождите 60 секунд и повторите запрос."
                    ),
                )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            logger.error("connect_telegram error (attempt %d): %s", attempt + 1, e)
            raise HTTPException(
                status_code=500, detail=f"Ошибка отправки кода: {error_str}",
            )

    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
    raise HTTPException(
        status_code=503, detail="Нет соединения с Telegram. Проверьте интернет.",
    )


@router.post("/telegram/confirm")
async def confirm_telegram(
    data: ChannelConfirmTelegram,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)
    channel = await repo.get_by_id(data.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Telegram channel not found")
    if channel.type != "telegram":
        raise HTTPException(status_code=400, detail="Invalid channel type")

    pending = _pending_auths.get(data.channel_id)
    if not pending:
        raise HTTPException(
            status_code=400,
            detail=(
                "Сессия аутентификации истекла. "
                "Запросите новый код через /telegram/connect"
            ),
        )

    client = pending.client
    phone = pending.phone

    try:
        await asyncio.wait_for(
            client.sign_in(
                phone_number=phone,
                phone_code=data.code,
                phone_code_hash=data.phone_code_hash,
            ),
            timeout=15,
        )

    except PhoneCodeExpired:
        return await _handle_code_expired(
            pending=pending,
            channel=channel,
            old_phone_code_hash=data.phone_code_hash,
        )

    except PhoneCodeInvalid:
        raise HTTPException(status_code=400, detail="Неверный код подтверждения")

    except FloodWait as e:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов. Подождите {e.value} секунд.",
        )

    except SessionPasswordNeeded:
        password = _stored_2fa_password()
        if password:
            try:
                await asyncio.wait_for(client.check_password(password), timeout=15)
            except Exception:
                password = None
        if not password:
            return {
                "status": "password_needed",
                "channel_id": data.channel_id,
                "message": "Требуется облачный пароль (2FA)",
            }

    except (asyncio.TimeoutError, Timeout, OSError):
        raise HTTPException(
            status_code=503,
            detail="Таймаут подключения к Telegram. Проверьте интернет и прокси.",
        )

    except Exception as e:
        error_str = str(e)
        if "PHONE_CODE_EXPIRED" in error_str:
            return await _handle_code_expired(
                pending=pending,
                channel=channel,
                old_phone_code_hash=data.phone_code_hash,
            )
        try:
            await client.disconnect()
        except Exception:
            pass
        if _pending_auths.get(data.channel_id) is pending:
            _pending_auths.pop(data.channel_id, None)
        logger.error(f"Telegram confirm error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error_str}")

    session_string = await client.export_session_string()
    _pending_auths.pop(data.channel_id, None)
    await client.disconnect()

    channel_service = ChannelService(session)
    await channel_service.update(
        int(channel.id),
        config={"phone": phone, "session_string": encrypt(session_string)},
        is_connected=True,
    )

    tg_cfg = await load_effective_telegram_config(session)
    background_tasks.add_task(
        _init_telegram_adapter,
        phone,
        session_string,
        tg_cfg["api_id"],
        tg_cfg["api_hash"],
        tg_cfg["proxy"],
    )

    return {
        "status": "connected",
        "message": "Telegram подключён",
    }


@router.post("/telegram/resend")
async def resend_telegram_code(
    data: ChannelResendTelegram,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    logger.info("resend_telegram_code: channel_id=%s", data.channel_id)
    pending = _pending_auths.get(data.channel_id)
    if not pending:
        raise HTTPException(
            status_code=400,
            detail=(
                "Сессия аутентификации истекла. "
                "Запросите код через /telegram/connect"
            ),
        )

    cooldown = _code_cooldown_remaining(data.channel_id)
    if cooldown > 0:
        raise HTTPException(
            status_code=429,
            detail=(
                "Слишком часто. Каждый новый запрос отменяет предыдущий код — "
                f"подождите {cooldown} секунд."
            ),
        )

    try:
        result = await asyncio.wait_for(
            pending.client.resend_code(pending.phone, data.phone_code_hash),
            timeout=20,
        )

        _mark_code_sent(data.channel_id)
        info = _parse_sent_code(result)
        logger.info(
            "resend OK: code_type=%s next_type=%s timeout=%s phone=%s",
            info.code_type, info.next_type, info.timeout, pending.phone,
        )
        if info.code_type == "sms":
            message = "Код отправлен по SMS"
        elif info.code_type == "call":
            message = "Код отправлен по звонку"
        else:
            message = "Код отправлен в Telegram"

        return {
            "status": "code_sent",
            "phone_code_hash": result.phone_code_hash,
            "code_type": info.code_type,
            "next_type": info.next_type,
            "timeout": info.timeout or 60,
            "message": message,
        }

    except FloodWait as e:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов. Подождите {e.value} секунд.",
        )
    except (Timeout, OSError, asyncio.TimeoutError):
        raise HTTPException(
            status_code=503, detail="Нет соединения с Telegram. Проверьте интернет."
        )
    except Exception as e:
        error_str = str(e)
        if "SEND_CODE_UNAVAILABLE" in error_str:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Код уже отправлен ранее. "
                    "Подождите 60 секунд и повторите запрос."
                ),
            )
        logger.error("Telegram resend error: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Ошибка повторной отправки: {error_str}",
        )


@router.post("/telegram/password")
async def password_telegram(
    data: ChannelPasswordTelegram,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    pending = _pending_auths.get(data.channel_id)
    if not pending:
        raise HTTPException(
            status_code=400,
            detail=(
                "Сессия аутентификации истекла. "
                "Запросите код через /telegram/connect"
            ),
        )

    client = pending.client

    try:
        await asyncio.wait_for(client.check_password(data.password), timeout=15)
    except FloodWait as e:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов. Подождите {e.value} секунд.",
        )
    except (asyncio.TimeoutError, Timeout, OSError):
        raise HTTPException(
            status_code=503,
            detail="Таймаут подключения к Telegram. Проверьте интернет и прокси.",
        )
    except Exception as e:
        logger.error(f"Telegram password error: {e}")
        raise HTTPException(status_code=400, detail="Неверный пароль")

    session_string = await client.export_session_string()
    _pending_auths.pop(data.channel_id, None)
    await client.disconnect()

    from ...channels.telegram import TelegramAdapter

    channel_service = ChannelService(session)
    await channel_service.update(
        data.channel_id,
        config={"phone": pending.phone, "session_string": encrypt(session_string)},
        is_connected=True,
    )

    from ...deps import get_poll_service

    tg_cfg = await load_effective_telegram_config(session)
    tg_adapter = TelegramAdapter()
    connected = await tg_adapter.connect(config={
        "api_id": tg_cfg["api_id"],
        "api_hash": tg_cfg["api_hash"],
        "phone": pending.phone,
        "session_string": session_string,
        "session_name": f"bizibox_{pending.phone}",
        "session_dir": "./data/sessions",
        "proxy": tg_cfg["proxy"],
    })
    if not connected:
        raise HTTPException(status_code=500, detail="Ошибка подключения Telegram адаптера")

    ps = get_poll_service()
    if ps:
        ps.register_channel("telegram", tg_adapter)
        ps.start(
            "telegram",
            await get_poll_interval(session, "telegram_poll_interval", settings.TELEGRAM_POLL_INTERVAL),
        )

    return {
        "status": "connected",
        "message": "Telegram подключён",
    }


