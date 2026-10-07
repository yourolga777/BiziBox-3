import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..channels.base import BaseChannelAdapter, ChannelFetchTimeoutError
from ..database import AsyncSessionLocal
from ..services.channel_message_service import ChannelMessageService

logger = logging.getLogger(__name__)


class PollService:
    def __init__(
        self,
        session_factory: Optional[Callable[[], AsyncSession]] = None,
        cms_factory: Optional[Callable[[AsyncSession], ChannelMessageService]] = None,
    ):
        self.channels: Dict[str, BaseChannelAdapter] = {}
        self.tasks: Dict[str, asyncio.Task[Any]] = {}
        self.last_poll: Dict[str, Optional[datetime]] = {}
        self._session_factory = session_factory
        self._cms_factory = cms_factory

    def _get_session_factory(self) -> Callable[[], AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return cast(Callable[[], AsyncSession], AsyncSessionLocal)

    def _get_cms_factory(self) -> Callable[[AsyncSession], ChannelMessageService]:
        return self._cms_factory or ChannelMessageService

    def register_channel(self, channel_type: str, adapter: BaseChannelAdapter) -> None:
        self.channels[channel_type] = adapter

    def get_channel(self, channel_type: str) -> Optional[BaseChannelAdapter]:
        return self.channels.get(channel_type)

    def is_running(self, channel_type: str) -> bool:
        task = self.tasks.get(channel_type)
        return task is not None and not task.done()

    async def poll_channel(self, channel_type: str, interval: int) -> None:
        logger.info(f"Polling started for {channel_type} (interval={interval}s)")
        try:
            while True:
                try:
                    adapter = self.channels.get(channel_type)
                    if not adapter:
                        logger.warning(
                            "No adapter for %s, stopping poll (deadline=%s)",
                            channel_type,
                            self.last_poll.get(channel_type),
                        )
                        break

                    since = self.last_poll.get(channel_type)

                    try:
                        messages = await adapter.fetch_messages(since=since)
                    except ChannelFetchTimeoutError as e:
                        logger.warning(
                            "Fetch timed out for %s — last_polled_at unchanged: %s",
                            channel_type,
                            e,
                        )
                        await asyncio.sleep(interval)
                        continue

                    # Время фиксируем ПОСЛЕ фактической доставки: при таймауте
                    # (выше) оно не обновляется и UI не показывает ложное
                    # «загружено только что».
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    self.last_poll[channel_type] = now
                    try:
                        async with self._get_session_factory()() as sess:
                            await sess.execute(
                                text(
                                    "UPDATE channels SET last_polled_at = :ts"
                                    " WHERE type = :t"
                                ),
                                {"ts": now, "t": channel_type},
                            )
                            await sess.commit()
                    except Exception as e:
                        logger.error(
                            "Failed to stamp last_polled_at for %s: %s",
                            channel_type,
                            e,
                        )

                    logger.debug(
                        "Fetched %d messages for %s since=%s",
                        len(messages),
                        channel_type,
                        since,
                    )

                    for msg in messages:
                        try:
                            async with self._get_session_factory()() as session:
                                cms = self._get_cms_factory()(session)
                                await cms.process_incoming(msg)
                                await session.commit()
                        except Exception as e:
                            logger.error(
                                "Error processing %s message: %s",
                                channel_type,
                                e,
                            )

                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(
                        "Polling error for %s (retry in %ss): %s",
                        channel_type,
                        interval,
                        e,
                    )
                    await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Polling cancelled for %s", channel_type)
        finally:
            self.last_poll[channel_type] = None
            logger.info("Poll stopped for %s", channel_type)

    def start(
        self,
        channel_type: str,
        interval: int,
        since: datetime | None = None,
    ) -> None:
        if channel_type in self.tasks and not self.tasks[channel_type].done():
            logger.warning(f"Polling already running for {channel_type}")
            return
        task = asyncio.create_task(self.poll_channel(channel_type, interval))
        self.tasks[channel_type] = task
        self.last_poll[channel_type] = since

    async def stop(self, channel_type: str) -> None:
        task = self.tasks.pop(channel_type, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def stop_all(self) -> None:
        for channel_type in list(self.tasks.keys()):
            await self.stop(channel_type)
