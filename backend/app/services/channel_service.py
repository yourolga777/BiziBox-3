import asyncio
import logging
from typing import Any, Optional

from cryptography.fernet import InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from ..channels.base import BaseChannelAdapter
from ..channels.email import EmailAdapter
from ..channels.telegram import TelegramAdapter
from ..channels.vk import VkAdapter
from ..config import settings
from ..models.channel import ChannelModel
from ..repositories.channel import ChannelRepository
from ..repositories.settings import SettingsRepository
from ..services.channel_message_service import ChannelMessageService
from ..services.poll_service import PollService
from ..services.telegram_config import load_effective_telegram_config
from ..user_context import get_active_login, get_user_data_dir
from ..utils.crypto import decrypt

logger = logging.getLogger(__name__)


class ChannelService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.repo = ChannelRepository(session, owner_id)

    async def create(
        self,
        channel_type: str,
        name: str = "",
        config: dict[str, Any] | None = None,
        is_connected: bool = False,
    ) -> ChannelModel:
        return await self.repo.create(
            type=channel_type,
            name=name or channel_type,
            config=config or {},
            is_connected=is_connected,
        )

    async def update(
        self,
        channel_id: int,
        config: dict[str, Any] | None = None,
        is_connected: bool | None = None,
    ) -> Optional[ChannelModel]:
        kwargs: dict[str, Any] = {}
        if config is not None:
            kwargs["config"] = config
        if is_connected is not None:
            kwargs["is_connected"] = is_connected
        return await self.repo.update(channel_id, **kwargs)

    async def get_or_create_telegram(self, phone: str) -> ChannelModel:
        existing = await self.repo.get_by_type("telegram")
        for ch in existing:
            if ch.is_connected:
                return ch
        if existing:
            channel = existing[0]
            await self.repo.update(channel.id, config={"phone": phone})
            return channel
        return await self.create(
            channel_type="telegram",
            name="Telegram",
            config={"phone": phone},
            is_connected=False,
        )

    async def reconnect_telegram(self) -> bool:
        """Переподключить Telegram-канал с текущим эффективным прокси.

        Используется при изменении proxy_config в настройках: останавливает
        текущий poll, отключает старый адаптер и подключает заново по
        сохранённой session_string.
        """
        from ..deps import get_poll_service
        from ..services.settings_service import get_poll_interval

        channels = await self.repo.get_by_type("telegram")
        connected = [c for c in channels if c.is_connected]
        if not connected:
            return False

        channel = connected[0]
        cfg: Any = self._with_user_paths(channel.config or {})
        if "session_string" not in cfg:
            return False

        ps = get_poll_service()
        if ps:
            await ps.stop("telegram")
            old_adapter = ps.get_channel("telegram")
            if old_adapter:
                try:
                    await old_adapter.disconnect()
                except Exception:
                    logger.warning(
                        "reconnect_telegram: failed to disconnect old adapter",
                        exc_info=True,
                    )

        tg_cfg = dict(cfg)
        tg_cfg["session_string"] = self._maybe_decrypt(tg_cfg["session_string"])
        effective = await load_effective_telegram_config(self.session, self.owner_id)
        tg_cfg["api_id"] = effective["api_id"]
        tg_cfg["api_hash"] = effective["api_hash"]
        tg_cfg["proxy"] = effective["proxy"]

        adapter = TelegramAdapter()
        connected_ok = await self._try_connect(adapter, tg_cfg)
        if not connected_ok:
            logger.error("reconnect_telegram: connect failed")
            return False

        if ps:
            ps.register_channel("telegram", adapter)
            ps.set_channel_mode("telegram", getattr(channel, "mode", "both") or "both")
            interval = await get_poll_interval(
                self.session,
                "telegram_poll_interval",
                settings.TELEGRAM_POLL_INTERVAL,
                self.owner_id,
            )
            ps.start("telegram", int(interval), since=channel.last_polled_at)
        logger.info("Telegram channel reconnected with updated proxy")
        return True

    def _with_user_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        login = get_active_login()
        if not login:
            return config
        user_dir = get_user_data_dir(login)
        cfg = dict(config)
        cfg.setdefault("data_dir", str(user_dir))
        cfg.setdefault("session_dir", str(user_dir / "sessions"))
        return cfg

    def _vk_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        vk_cfg = dict(cfg)
        if "token" in vk_cfg:
            vk_cfg["token"] = self._maybe_decrypt(vk_cfg["token"])
        vk_cfg.setdefault("group_id", settings.VK_GROUP_ID)
        if not vk_cfg.get("token"):
            vk_cfg["token"] = settings.VK_ACCESS_TOKEN
        return vk_cfg

    async def restore_channels(
        self,
        poll_service: PollService,
    ) -> None:
        connected = await self.repo.get_connected()
        if not connected:
            return

        settings_repo = SettingsRepository(self.session)
        tg_interval = await settings_repo.get("telegram_poll_interval")
        email_interval = await settings_repo.get("email_poll_interval")
        vk_interval = await settings_repo.get("vk_poll_interval")
        if tg_interval is None:
            tg_interval = settings.TELEGRAM_POLL_INTERVAL
        if email_interval is None:
            email_interval = settings.EMAIL_POLL_INTERVAL
        if vk_interval is None:
            vk_interval = settings.VK_POLL_INTERVAL

        for channel in connected:
            cfg: Any = self._with_user_paths(channel.config or {})
            restored = False
            last_error: Exception | None = None
            marked_disconnected = False

            for attempt in range(3):
                try:
                    if channel.type == "telegram":
                        adapter: BaseChannelAdapter = TelegramAdapter()
                        tg_cfg = dict(cfg)
                        if "session_string" in tg_cfg:
                            tg_cfg["session_string"] = decrypt(tg_cfg["session_string"])
                        effective = await load_effective_telegram_config(
                            self.session, self.owner_id
                        )
                        tg_cfg["api_id"] = effective["api_id"]
                        tg_cfg["api_hash"] = effective["api_hash"]
                        tg_cfg["proxy"] = effective["proxy"]
                        connected_ok = await asyncio.wait_for(
                            adapter.connect(tg_cfg), timeout=15
                        )
                        if connected_ok:
                            poll_service.register_channel("telegram", adapter)
                            poll_service.set_channel_mode(
                                "telegram", getattr(channel, "mode", "both") or "both"
                            )
                            poll_service.start(
                                "telegram",
                                int(tg_interval),
                                since=channel.last_polled_at,
                            )
                            logger.info("Restored Telegram channel")
                            restored = True
                            break
                        else:
                            last_error = Exception("connect returned False")

                    elif channel.type == "email":
                        adapter = EmailAdapter()
                        email_cfg = dict(cfg)
                        if "password" in email_cfg:
                            email_cfg["password"] = self._maybe_decrypt(email_cfg["password"])
                        connected_ok = await asyncio.wait_for(
                            adapter.connect(email_cfg), timeout=15
                        )
                        if connected_ok:
                            poll_service.register_channel("email", adapter)
                            poll_service.set_channel_mode(
                                "email", getattr(channel, "mode", "both") or "both"
                            )
                            poll_service.start(
                                "email",
                                int(email_interval),
                                since=channel.last_polled_at,
                            )
                            logger.info("Restored Email channel")
                            restored = True
                            break
                        else:
                            last_error = Exception("connect returned False")

                    elif channel.type == "vk":
                        adapter = VkAdapter()
                        connected_ok = await asyncio.wait_for(
                            adapter.connect(self._vk_config(cfg)), timeout=15
                        )
                        if connected_ok:
                            poll_service.register_channel("vk", adapter)
                            poll_service.set_channel_mode(
                                "vk", getattr(channel, "mode", "both") or "both"
                            )
                            poll_service.start(
                                "vk",
                                int(vk_interval),
                                since=channel.last_polled_at,
                            )
                            logger.info("Restored VK channel")
                            restored = True
                            break
                        else:
                            last_error = Exception("connect returned False")

                except InvalidToken:
                    last_error = InvalidToken("decryption failed — invalid key")
                    logger.error("Decryption failed for %s channel — marking disconnected", channel.type)
                    await self.repo.update(channel.id, is_connected=False)
                    marked_disconnected = True
                    break
                except asyncio.TimeoutError:
                    last_error = asyncio.TimeoutError("connection timed out")
                except Exception as e:
                    last_error = e

                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

            if not restored:
                logger.warning(
                    "Failed to restore %s channel after 3 attempts: %s",
                    channel.type, last_error,
                )
                if not marked_disconnected:
                    await self.repo.update(channel.id, is_connected=False)

    async def startup_load(
        self,
        poll_service: PollService,
    ) -> dict[str, Any]:
        channels = await self.repo.get_all(skip=0, limit=1000)
        results: list[dict[str, Any]] = []
        total_new = 0

        for channel in channels:
            entry: dict[str, Any] = {
                "type": channel.type,
                "name": channel.name or channel.type,
                "connected": False,
                "new_messages": 0,
                "error": None,
            }

            adapter = poll_service.get_channel(channel.type)
            if adapter is None:
                try:
                    adapter = await self._connect_saved(channel)
                    if adapter is not None:
                        poll_service.register_channel(channel.type, adapter)
                        logger.info("Startup: connected %s channel", channel.type)
                except Exception as e:
                    logger.error("Startup: connect %s failed: %s", channel.type, e)
                    entry["error"] = str(e)
                    results.append(entry)
                    continue

            if adapter is None:
                results.append(entry)
                continue

            entry["connected"] = True
            try:
                messages = await adapter.fetch_messages(
                    since=channel.last_polled_at,
                )
            except Exception as e:
                logger.error("Startup: fetch %s failed: %s", channel.type, e)
                entry["error"] = str(e)
                results.append(entry)
                continue

            new_count = 0
            for msg in messages:
                try:
                    cms = ChannelMessageService(self.session)
                    result = await cms.process_incoming(msg)
                    await self.session.commit()
                    if result is not None:
                        new_count += 1
                except Exception:
                    await self.session.rollback()

            entry["new_messages"] = new_count
            total_new += new_count
            results.append(entry)

        return {"channels": results, "total_new": total_new}

    async def _poll_interval(self, channel_type: str) -> int:
        settings_repo = SettingsRepository(self.session)
        if channel_type == "telegram":
            key, default = "telegram_poll_interval", settings.TELEGRAM_POLL_INTERVAL
        elif channel_type == "vk":
            key, default = "vk_poll_interval", settings.VK_POLL_INTERVAL
        else:
            key, default = "email_poll_interval", settings.EMAIL_POLL_INTERVAL
        value = await settings_repo.get(key)
        if value is None:
            value = default
        return int(value)

    async def reconnect_disconnected(self, poll_service: PollService) -> int:
        """Переподключает каналы с is_connected=False (например, отвалившиеся при
        старте без сети), чтобы они поднялись без ручного «Переподключить»."""
        disconnected = await self.repo.get_disconnected()
        reconnected = 0
        for channel in disconnected:
            if poll_service.is_running(channel.type):
                continue
            adapter = await self._connect_saved(channel)
            if adapter is None:
                continue
            poll_service.register_channel(channel.type, adapter)
            poll_service.set_channel_mode(
                channel.type, getattr(channel, "mode", "both") or "both"
            )
            interval = await self._poll_interval(channel.type)
            poll_service.start(channel.type, interval, since=channel.last_polled_at)
            await self.repo.update(channel.id, is_connected=True)
            logger.info("Reconnected %s channel after disconnect", channel.type)
            reconnected += 1
        return reconnected

    async def _connect_saved(
        self,
        channel: ChannelModel,
    ) -> Optional[BaseChannelAdapter]:
        cfg: Any = self._with_user_paths(channel.config or {})
        if channel.type == "telegram":
            if "session_string" not in cfg:
                return None
            adapter: BaseChannelAdapter = TelegramAdapter()
            tg_cfg = dict(cfg)
            tg_cfg["session_string"] = self._maybe_decrypt(tg_cfg["session_string"])
            effective = await load_effective_telegram_config(
                self.session, self.owner_id
            )
            tg_cfg["api_id"] = effective["api_id"]
            tg_cfg["api_hash"] = effective["api_hash"]
            tg_cfg["proxy"] = effective["proxy"]
            connected = await self._try_connect(adapter, tg_cfg)
            return adapter if connected else None

        if channel.type == "email":
            if "password" not in cfg:
                return None
            adapter = EmailAdapter()
            email_cfg = dict(cfg)
            email_cfg["password"] = self._maybe_decrypt(email_cfg["password"])
            connected = await self._try_connect(adapter, email_cfg)
            return adapter if connected else None

        if channel.type == "vk":
            if "token" not in cfg and not settings.VK_ACCESS_TOKEN:
                return None
            adapter = VkAdapter()
            connected = await self._try_connect(adapter, self._vk_config(cfg))
            return adapter if connected else None

        return None

    @staticmethod
    async def _try_connect(
        adapter: BaseChannelAdapter,
        config: dict[str, Any],
    ) -> bool:
        try:
            return await asyncio.wait_for(adapter.connect(config), timeout=15)
        except asyncio.TimeoutError:
            return False

    @staticmethod
    def _maybe_decrypt(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return decrypt(value)
        except InvalidToken:
            return value
