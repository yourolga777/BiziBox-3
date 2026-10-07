import logging
from typing import Any

from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_session
from ...deps import get_poll_service
from ...repositories.channel import ChannelRepository
from ...schemas.channel import ChannelConnectVK
from ...services.settings_service import get_poll_interval
from ...utils.crypto import decrypt, encrypt
from .base import router

logger = logging.getLogger(__name__)


@router.post("/vk/connect")
async def connect_vk(
    data: ChannelConnectVK,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)

    existing = await repo.get_by_type("vk")
    for ch in existing:
        if ch.is_connected:
            raise HTTPException(status_code=400, detail="VK already connected")

    group_id = data.group_id or settings.VK_GROUP_ID
    token = data.token or settings.VK_ACCESS_TOKEN
    if not group_id or not token:
        raise HTTPException(
            status_code=400, detail="Укажите group_id и token VK (или заполните .env)"
        )

    config = {"group_id": group_id, "token": encrypt(token)}

    if existing:
        channel = existing[0]
        await repo.update(channel.id, config=config)
    else:
        channel = await repo.create(
            type="vk",
            name="VK",
            config=config,
            is_connected=False,
        )

    await session.commit()

    try:
        from ...channels.vk import VkAdapter

        adapter = VkAdapter()
        connected = await adapter.connect({"group_id": group_id, "token": token})
        if not connected:
            raise HTTPException(
                status_code=400, detail="Ошибка подключения к VK. Проверьте токен."
            )

        await repo.update(channel.id, is_connected=True)
        await session.commit()

        ps = get_poll_service()
        if ps:
            ps.register_channel("vk", adapter)
            ps.start(
                "vk",
                await get_poll_interval(
                    session, "vk_poll_interval", settings.VK_POLL_INTERVAL
                ),
            )
            if not ps.is_running("vk"):
                logger.error("VK poll failed to start after connect")
        else:
            logger.error("Poll service unavailable — VK poll not started")

        return {
            "status": "connected",
            "message": "VK подключён",
            "polling": bool(ps and ps.is_running("vk")) if ps else False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VK connect error: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {str(e)}")


@router.post("/vk/reconnect-stored")
async def reconnect_vk_stored(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)

    existing = await repo.get_by_type("vk")
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="VK канал не найден. Сначала подключите его.",
        )

    channel = existing[0]
    cfg: Any = channel.config or {}
    group_id = cfg.get("group_id") or settings.VK_GROUP_ID
    token: Any = cfg.get("token") or settings.VK_ACCESS_TOKEN

    if not group_id:
        raise HTTPException(
            status_code=400,
            detail="Сохранённый group_id не найден. Подключитесь заново.",
        )

    try:
        from ...channels.vk import VkAdapter

        try:
            token = decrypt(token)
        except InvalidToken:
            pass

        ps = get_poll_service()
        if ps:
            old_adapter = ps.get_channel("vk")
            if old_adapter:
                try:
                    await old_adapter.disconnect()
                except Exception:
                    pass
            await ps.stop("vk")

        adapter = VkAdapter()
        connected = await adapter.connect({"group_id": group_id, "token": token})
        if not connected:
            raise HTTPException(
                status_code=400, detail="Ошибка подключения к VK. Проверьте токен."
            )

        await repo.update(channel.id, is_connected=True)
        await session.commit()

        if ps:
            ps.register_channel("vk", adapter)
            ps.start(
                "vk",
                await get_poll_interval(
                    session, "vk_poll_interval", settings.VK_POLL_INTERVAL
                ),
            )
            if not ps.is_running("vk"):
                logger.error("VK poll failed to start after reconnect")
        else:
            logger.error("Poll service unavailable — VK poll not started")

        return {
            "status": "connected",
            "message": "VK переподключён",
            "polling": bool(ps and ps.is_running("vk")) if ps else False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VK reconnect-stored error: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка переподключения: {str(e)}")
