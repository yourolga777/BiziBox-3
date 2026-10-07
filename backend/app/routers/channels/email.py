import logging
from typing import Any

from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_session
from ...deps import get_poll_service
from ...repositories.channel import ChannelRepository
from ...schemas.channel import ChannelConnectEmail
from ...services.settings_service import get_poll_interval
from ...utils.crypto import encrypt
from .base import router

logger = logging.getLogger(__name__)


@router.post("/email/connect")
async def connect_email(
    data: ChannelConnectEmail,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)

    existing = await repo.get_by_type("email")
    for ch in existing:
        if ch.is_connected:
            raise HTTPException(status_code=400, detail="Email already connected")

    encrypted_password = encrypt(data.password)
    config = {
        "email": data.email,
        "password": encrypted_password,
        "imap_host": data.imap_host,
        "smtp_host": data.smtp_host,
        "imap_port": data.imap_port,
        "smtp_port": data.smtp_port,
    }

    if existing:
        channel = existing[0]
        await repo.update(channel.id, config=config)
    else:
        channel = await repo.create(
            type="email",
            name=data.email,
            config=config,
            is_connected=False,
        )

    await session.commit()

    try:
        from ...channels.email import EmailAdapter
        from ...utils.crypto import decrypt

        adapter = EmailAdapter()
        connect_config = dict(config)
        connect_config["password"] = decrypt(encrypted_password)

        connected = await adapter.connect(connect_config)
        if not connected:
            raise HTTPException(status_code=400, detail="Ошибка подключения к почте")

        await repo.update(channel.id, is_connected=True)
        await session.commit()

        ps = get_poll_service()
        if ps:
            ps.register_channel("email", adapter)
            ps.start("email", await get_poll_interval(session, "email_poll_interval", settings.EMAIL_POLL_INTERVAL))
            if not ps.is_running("email"):
                logger.error("Email poll failed to start after connect")
        else:
            logger.error("Poll service unavailable — email poll not started")

        return {
            "status": "connected",
            "message": "Email подключён",
            "polling": bool(ps and ps.is_running("email")) if ps else False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email connect error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {str(e)}")


@router.post("/email/reconnect")
async def reconnect_email(
    data: ChannelConnectEmail,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)

    existing = await repo.get_by_type("email")
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Email канал не найден. Сначала подключите его.",
        )

    channel = existing[0]
    encrypted_password = encrypt(data.password)
    config = {
        "email": data.email,
        "password": encrypted_password,
        "imap_host": data.imap_host,
        "smtp_host": data.smtp_host,
        "imap_port": data.imap_port,
        "smtp_port": data.smtp_port,
    }

    await repo.update(channel.id, config=config, is_connected=False)
    await session.commit()

    try:
        from ...channels.email import EmailAdapter
        from ...utils.crypto import decrypt

        ps = get_poll_service()
        if ps:
            old_adapter = ps.get_channel("email")
            if old_adapter:
                try:
                    await old_adapter.disconnect()
                except Exception:
                    pass
            await ps.stop("email")

        adapter = EmailAdapter()
        connect_config = dict(config)
        connect_config["password"] = decrypt(encrypted_password)

        connected = await adapter.connect(connect_config)
        if not connected:
            raise HTTPException(
                status_code=400,
                detail="Ошибка подключения к почте. Проверьте данные.",
            )

        await repo.update(channel.id, is_connected=True)
        await session.commit()

        if ps:
            ps.register_channel("email", adapter)
            ps.start("email", await get_poll_interval(session, "email_poll_interval", settings.EMAIL_POLL_INTERVAL))
            if not ps.is_running("email"):
                logger.error("Email poll failed to start after reconnect")
        else:
            logger.error("Poll service unavailable — email poll not started")

        return {
            "status": "connected",
            "message": "Email переподключён",
            "polling": bool(ps and ps.is_running("email")) if ps else False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email reconnect error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка переподключения: {str(e)}")


@router.post("/email/reconnect-stored")
async def reconnect_email_stored(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)

    existing = await repo.get_by_type("email")
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Email канал не найден. Сначала подключите его.",
        )

    channel = existing[0]
    cfg: Any = channel.config or {}
    encrypted_password = cfg.get("password")
    if not encrypted_password:
        raise HTTPException(
            status_code=400,
            detail="Сохранённый пароль не найден. Переподключитесь с паролем.",
        )

    await session.commit()

    try:
        from ...channels.email import EmailAdapter
        from ...utils.crypto import decrypt

        try:
            password = decrypt(encrypted_password)
        except InvalidToken:
            password = encrypted_password

        ps = get_poll_service()
        if ps:
            old_adapter = ps.get_channel("email")
            if old_adapter:
                try:
                    await old_adapter.disconnect()
                except Exception:
                    pass
            await ps.stop("email")

        adapter = EmailAdapter()
        connect_config = {
            "email": cfg["email"],
            "password": password,
            "imap_host": cfg.get("imap_host", ""),
            "smtp_host": cfg.get("smtp_host", ""),
            "imap_port": cfg.get("imap_port", 993),
            "smtp_port": cfg.get("smtp_port", 465),
        }

        connected = await adapter.connect(connect_config)
        if not connected:
            raise HTTPException(
                status_code=400,
                detail="Ошибка подключения к почте. Проверьте данные.",
            )

        await repo.update(channel.id, is_connected=True)
        await session.commit()

        if ps:
            ps.register_channel("email", adapter)
            ps.start("email", await get_poll_interval(session, "email_poll_interval", settings.EMAIL_POLL_INTERVAL))
            if not ps.is_running("email"):
                logger.error("Email poll failed to start after reconnect")
        else:
            logger.error("Poll service unavailable — email poll not started")

        return {
            "status": "connected",
            "message": "Email переподключён",
            "polling": bool(ps and ps.is_running("email")) if ps else False,
        }
    except HTTPException:
        raise
    except InvalidToken:
        logger.error("Reconnect failed: decryption key mismatch")
        raise HTTPException(
            status_code=500,
            detail="Ошибка расшифровки пароля. Переподключитесь с паролем заново.",
        )
    except Exception as e:
        logger.error(f"Email reconnect-stored error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка переподключения: {str(e)}")
