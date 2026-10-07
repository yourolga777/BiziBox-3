import logging
import os
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...channels.base import ChannelFetchTimeoutError
from ...database import get_session
from ...deps import get_poll_service
from ...repositories.channel import ChannelRepository
from ...schemas.channel import ChannelResponse, DownloadResponse
from ...services.channel_message_service import ChannelMessageService
from .auth import _pending_auths
from .telegram_debug import router as telegram_debug_router

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(telegram_debug_router)


@router.get("/", response_model=List[ChannelResponse])
async def get_channels(
    session: AsyncSession = Depends(get_session),
) -> list[ChannelResponse]:
    repo = ChannelRepository(session)
    channels = await repo.get_all()
    return [ChannelResponse.model_validate(c) for c in channels]


@router.post("/{channel_type}/download")
async def download_messages(
    channel_type: str,
    session: AsyncSession = Depends(get_session),
) -> DownloadResponse:
    repo = ChannelRepository(session)
    channels = await repo.get_by_type(channel_type)
    if not channels:
        raise HTTPException(status_code=404, detail=f"Channel {channel_type} not found")

    ps = get_poll_service()
    adapter = ps.get_channel(channel_type) if ps else None
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail=f"Adapter for {channel_type} not connected",
        )

    try:
        messages = await adapter.fetch_messages(since=channels[0].last_polled_at)
    except ChannelFetchTimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail=f"Таймаут загрузки канала {channel_type}. Попробуйте позже.",
        ) from e

    new_count = 0
    for msg in messages:
        try:
            cms = ChannelMessageService(session)
            result = await cms.process_incoming(msg)
            await session.commit()
            if result is not None:
                new_count += 1
        except Exception:
            await session.rollback()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if ps:
        ps.last_poll[channel_type] = now

    await session.execute(
        text("UPDATE channels SET last_polled_at = :ts WHERE type = :t"),
        {"ts": now, "t": channel_type},
    )
    await session.commit()

    return DownloadResponse(new_messages=new_count, last_polled_at=now)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
) -> ChannelResponse:
    repo = ChannelRepository(session)
    channel = await repo.get_by_id(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse.model_validate(channel)


@router.get("/{channel_id}/health")
async def channel_health(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)
    channel = await repo.get_by_id(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    ps = get_poll_service()
    adapter = ps.get_channel(channel.type) if ps else None

    alive = False
    if adapter:
        if channel.type == "email":
            from ...channels.email import EmailAdapter
            if isinstance(adapter, EmailAdapter):
                alive = adapter.imap is not None or adapter.smtp is not None
        elif channel.type == "telegram":
            client = getattr(adapter, "client", None)
            alive = client is not None and getattr(client, "is_connected", False)
        elif channel.type == "vk":
            alive = getattr(adapter, "_client", None) is not None

    return {
        "channel_id": channel_id,
        "type": channel.type,
        "is_connected_db": channel.is_connected,
        "adapter_alive": alive,
        "needs_reconnect": channel.is_connected and not alive,
    }


@router.delete("/{channel_id}")
async def disconnect_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = ChannelRepository(session)
    channel = await repo.get_by_id(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    config: Any = channel.config or {}
    phone = config.get("phone") if channel.type == "telegram" else None

    ps = get_poll_service()
    adapter = None
    if ps:
        adapter = ps.get_channel(channel.type)
    if adapter:
        try:
            await adapter.disconnect()
        except Exception as e:
            logger.error(f"Disconnect error for {channel.type}: {e}")

    if ps:
        try:
            await ps.stop(channel.type)
        except Exception as e:
            logger.error(f"Stop poll error for {channel.type}: {e}")

    pending = _pending_auths.pop(int(channel.id), None)
    if pending is not None:
        try:
            await pending.client.disconnect()
            logger.info("Cleaned up pending auth for channel %s", channel.id)
        except Exception as e:
            logger.warning("Failed to disconnect pending client for channel %s: %s", channel.id, e)

    await repo.delete(channel_id)

    if phone:
        session_dir = "./data/sessions"
        session_file = os.path.join(session_dir, f"bizibox_{phone}.session")
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                logger.info(f"Removed session file: {session_file}")
        except Exception as e:
            logger.error(f"Failed to remove session file: {e}")

    return {"status": "disconnected", "message": f"{channel.name} удалён"}
