import asyncio
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from pyrogram import Client  # type: ignore[attr-defined]
from pyrogram.enums import ChatType
from pyrogram.types import Dialog, Message

from ..config import settings
from .base import BaseChannelAdapter, ChannelFetchTimeoutError

logger = logging.getLogger(__name__)


def _build_proxy() -> dict[str, Any] | None:
    if not settings.TELEGRAM_PROXY_ENABLED:
        return None
    proxy: dict[str, Any] = {
        "scheme": settings.TELEGRAM_PROXY_TYPE,
        "hostname": settings.TELEGRAM_PROXY_HOST,
        "port": settings.TELEGRAM_PROXY_PORT,
    }
    if settings.TELEGRAM_PROXY_TYPE == "mtproto" and settings.TELEGRAM_PROXY_SECRET:
        proxy["secret"] = settings.TELEGRAM_PROXY_SECRET
    elif settings.TELEGRAM_PROXY_USERNAME and settings.TELEGRAM_PROXY_PASSWORD:
        proxy["username"] = settings.TELEGRAM_PROXY_USERNAME
        proxy["password"] = settings.TELEGRAM_PROXY_PASSWORD
    return proxy


def _mime_extension(mime_type: str | None) -> str:
    if not mime_type:
        return ""
    mime_to_ext = {
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "application/msword": ".doc",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "text/html": ".html",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "video/mp4": ".mp4",
    }
    return mime_to_ext.get(mime_type, "")


class TelegramAdapter(BaseChannelAdapter):
    channel_type = "telegram"

    FETCH_TIMEOUT_SECONDS: float = 300

    def __init__(self) -> None:
        self.client: Client | None = None
        self._config: dict[str, Any] | None = None

    async def connect(self, config: dict[str, Any]) -> bool:
        self._config = dict(config)
        session_dir = config.get("session_dir", "./data/sessions")

        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        if not api_id or not api_hash:
            logger.error("Telegram connect error: api_id and api_hash are required")
            self.client = None
            return False

        session_string = config.get("session_string")
        proxy = config.get("proxy") if "proxy" in config else _build_proxy()
        try:
            if session_string:
                self.client = Client(
                    name=config.get("session_name", "bizibox"),
                    api_id=api_id,
                    api_hash=api_hash,
                    session_string=session_string,
                    proxy=proxy,  # type: ignore[arg-type]
                )
            else:
                os.makedirs(session_dir, exist_ok=True)
                self.client = Client(
                    name=config.get("session_name", "bizibox"),
                    api_id=api_id,
                    api_hash=api_hash,
                    phone_number=config.get("phone"),  # type: ignore[arg-type]
                    workdir=session_dir,
                    proxy=proxy,  # type: ignore[arg-type]
                )
            await asyncio.wait_for(self.client.start(), timeout=20)
            return True
        except (asyncio.TimeoutError, Exception) as e:
            logger.error("Telegram connect error: %s", e)
            try:
                if self.client is not None:
                    await self.client.stop()
            except Exception:
                pass
            self.client = None
            return False

    async def disconnect(self) -> None:
        if self.client:
            await self.client.stop()
            self.client = None

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        if not self.client and self._config:
            try:
                await self.connect(self._config)
            except Exception:
                pass
        if not self.client:
            return []

        try:
            return await asyncio.wait_for(
                self._fetch_messages(since=since, limit=limit),
                timeout=self.FETCH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Fetch timed out after {self.FETCH_TIMEOUT_SECONDS}s")
            raise ChannelFetchTimeoutError(
                f"Telegram fetch timed out after {self.FETCH_TIMEOUT_SECONDS}s"
            )
        except Exception as e:
            # Обрыв соединения (VPN/интернет): переподключаемся, чтобы канал
            # не «слетал» — следующий цикл polling продолжится с новым клиентом.
            logger.warning("Telegram fetch error — reconnecting: %s", e)
            await self.disconnect()
            if self._config:
                try:
                    await self.connect(self._config)
                except Exception:
                    pass
            raise

    async def _fetch_messages(
        self,
        since: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        # Первый запуск (since=None) — окно за последние 24 часа.
        if since is None:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                hours=24
            )

        messages: list[dict[str, Any]] = []
        total_fetched = 0
        page_size = 10
        dialog_count = 0

        async for dialog in self.client.get_dialogs():  # type: ignore[union-attr]
            if total_fetched >= limit:
                break

            dialog_count += 1

            # Диалог не обновлялся с since — пропускаем целиком.
            top = getattr(dialog, "top_message", None)
            if top is not None and top.date.replace(tzinfo=None) < since:
                continue

            is_read = dialog.unread_messages_count == 0
            contact_type = self._get_contact_type(dialog)
            contact_name = self._get_contact_name(dialog)
            contact_username = getattr(dialog.chat, "username", None) or None
            contact_id = str(dialog.chat.id)

            dialog_fetched = 0
            offset_id = 0
            while total_fetched < limit:
                page = [
                    msg
                    async for msg in self.client.get_chat_history(  # type: ignore[union-attr]
                        dialog.chat.id,
                        limit=page_size,
                        offset_id=offset_id,
                    )
                ]
                if not page:
                    break

                reached_since = False
                for msg in page:
                    if msg.date.replace(tzinfo=None) < since:
                        reached_since = True
                        break

                    attachments = self._extract_attachments(msg)
                    if not msg.text and not attachments:
                        continue

                    messages.append(
                        {
                            "channel": "telegram",
                            "channel_id": str(msg.chat.id),
                            "message_id": str(msg.id),
                            "direction": "incoming" if not msg.outgoing else "outgoing",
                            "contact_id": contact_id,
                            "contact_name": contact_name,
                            "contact_username": contact_username,
                            "contact_type": contact_type,
                            "content": msg.text or msg.caption or "",
                            "reply_to": (
                                str(msg.reply_to_message_id)
                                if msg.reply_to_message
                                else None
                            ),
                            "status": "read" if (is_read or msg.outgoing) else "unread",
                            "created_at": msg.date.replace(tzinfo=None),
                            "attachments": attachments,
                        }
                    )
                    total_fetched += 1
                    dialog_fetched += 1
                    if total_fetched >= limit:
                        break

                if reached_since or len(page) < page_size:
                    break
                offset_id = page[-1].id

            if dialog_fetched > 0:
                logger.info(
                    "Dialog %d: chat=%s (%s), fetched %d msgs (total=%d)",
                    dialog_count, contact_id, contact_name,
                    dialog_fetched, total_fetched,
                )

        logger.info(
            "Fetch complete: %d dialogs scanned, %d messages total",
            dialog_count, total_fetched,
        )
        return messages

    async def fetch_older_messages(
        self,
        chat_id: str,
        offset_id: int = 0,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Загрузить *limit* более ранних сообщений из конкретного чата.

        Используется кнопкой «Загрузить ещё N» в UI. Возвращает raw-словари
        для передачи в ChannelMessageService.process_incoming().
        """
        if not self.client:
            return []

        messages: list[dict[str, Any]] = []
        async for msg in self.client.get_chat_history(  # type: ignore[union-attr]
            int(chat_id),
            limit=limit,
            offset_id=offset_id,
        ):
            attachments = self._extract_attachments(msg)
            if not msg.text and not attachments:
                continue
            messages.append(
                {
                    "channel": "telegram",
                    "channel_id": str(msg.chat.id),
                    "message_id": str(msg.id),
                    "direction": "incoming" if not msg.outgoing else "outgoing",
                    "contact_id": chat_id,
                    "content": msg.text or msg.caption or "",
                    "reply_to": (
                        str(msg.reply_to_message_id)
                        if msg.reply_to_message
                        else None
                    ),
                    "status": "read" if msg.outgoing else "unread",
                    "created_at": msg.date.replace(tzinfo=None),
                    "attachments": attachments,
                }
            )

        logger.info(
            "fetch_older_messages: chat=%s, offset_id=%d, loaded=%d",
            chat_id, offset_id, len(messages),
        )
        return messages

    async def send_message(
        self,
        channel_id: str,
        text: str,
        reply_to: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        if not self.client:
            raise Exception("Telegram client not connected")

        try:
            chat_id = int(channel_id)
            reply_id = int(reply_to) if reply_to else None

            msg = await self.client.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_id,  # type: ignore[arg-type]
            )

            return {
                "channel": "telegram",
                "channel_id": str(msg.chat.id),
                "message_id": str(msg.id),
                "content": msg.text,
                "created_at": msg.date.replace(tzinfo=None),
            }
        except Exception as e:
            raise Exception(f"Telegram send error: {e}")

    async def send_file(
        self,
        channel_id: str,
        file_path: str,
        file_name: str | None = None,
        mime_type: str | None = None,
        reply_to: str | None = None,
        caption: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        if not self.client:
            raise Exception("Telegram client not connected")

        try:
            chat_id = int(channel_id)
            reply_id = int(reply_to) if reply_to else None
            caption_value = caption or ""

            if mime_type and mime_type.startswith("image/"):
                msg = await self.client.send_photo(
                    chat_id=chat_id,
                    photo=file_path,
                    caption=caption_value or None,  # type: ignore[arg-type]
                    reply_to_message_id=reply_id,  # type: ignore[arg-type]
                )
            else:
                msg = await self.client.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    file_name=file_name,  # type: ignore[arg-type]
                    caption=caption_value or None,  # type: ignore[arg-type]
                    reply_to_message_id=reply_id,  # type: ignore[arg-type]
                )

            if msg is None:
                raise Exception("Telegram returned no message")

            return {
                "channel": "telegram",
                "channel_id": str(msg.chat.id),
                "message_id": str(msg.id),
                "content": caption or "",
                "created_at": msg.date.replace(tzinfo=None),
            }
        except Exception as e:
            raise Exception(f"Telegram send file error: {e}")

    async def resolve_channel_id(self, recipient: str) -> str:
        if not self.client:
            raise Exception("Telegram client not connected")
        username = recipient.strip().lstrip("@")
        try:
            entity = await self.client.get_input_entity(username)  # type: ignore[attr-defined]
            return str(getattr(entity, "user_id", None) or getattr(entity, "chat_id", None))
        except Exception as e:
            raise Exception(f"Telegram: не удалось найти пользователя @{username}: {e}")

    async def get_dialog(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.client:
            return []

        messages = []
        async for msg in self.client.get_chat_history(  # type: ignore[union-attr]
            int(channel_id),
            limit=limit,
        ):
            attachments = self._extract_attachments(msg)
            if not msg.text and not msg.caption and not attachments:
                continue
            messages.append(
                {
                    "channel": "telegram",
                    "message_id": str(msg.id),
                    "direction": "incoming" if not msg.outgoing else "outgoing",
                    "content": msg.text or msg.caption or "",
                    "reply_to": (
                        str(msg.reply_to_message_id)
                        if msg.reply_to_message
                        else None
                    ),
                    "status": "read" if msg.outgoing else "unread",
                    "created_at": msg.date.replace(tzinfo=None),
                    "attachments": attachments,
                }
            )

        return messages

    async def download_file(self, file_path: str | None) -> io.BytesIO:
        if not self.client:
            raise Exception("Telegram client not connected")
        if not file_path:
            raise Exception("Attachment has no file reference")

        try:
            file = await self.client.download_media(
                file_path,
                in_memory=True,
            )
        except Exception as e:
            raise Exception(f"Telegram download error: {e}")

        if file is None:
            raise Exception("Telegram download returned no file")

        if isinstance(file, str):
            with open(file, "rb") as f:
                return io.BytesIO(f.read())
        if isinstance(file, bytes):
            return io.BytesIO(file)
        # BytesIO от download_media(in_memory=True) приходит с позицией в конце
        # буфера — перематываем, иначе read() вернёт пустые байты.
        file.seek(0)
        data = file.read()
        return io.BytesIO(data)

    def _extract_attachments(self, msg: Message) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        media_fields = [
            "document",
            "video",
            "audio",
            "voice",
            "video_note",
            "sticker",
            "animation",
        ]

        for field in media_fields:
            media = getattr(msg, field, None)
            if media is None:
                continue
            attachments.append(self._media_meta(media, msg.id))

        photo = getattr(msg, "photo", None)
        if photo is not None:
            photos = photo if isinstance(photo, (list, tuple)) else [photo]
            for idx, p in enumerate(photos):
                largest = p
                sizes = getattr(p, "sizes", None)
                if sizes:
                    try:
                        largest = max(
                            sizes,
                            key=lambda s: (getattr(s, "file_size", 0) or 0),
                        )
                    except (TypeError, ValueError):
                        largest = p
                attachments.append(
                    {
                        "file_path": getattr(largest, "file_id", None),
                        "file_name": f"photo_{msg.id}_{idx}.jpg",
                        "file_size": getattr(largest, "file_size", None),
                        "mime_type": "image/jpeg",
                    }
                )

        return attachments

    @staticmethod
    def _media_meta(media: Any, message_id: int) -> dict[str, Any]:
        file_id = getattr(media, "file_id", None)
        file_size = getattr(media, "file_size", None)
        mime_type = getattr(media, "mime_type", None)
        file_name = getattr(media, "file_name", None)
        if not file_name:
            extension = _mime_extension(mime_type) if mime_type else ""
            file_name = f"file_{message_id}{extension}"
        return {
            "file_path": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
        }

    def _get_contact_type(self, dialog: Dialog) -> str:
        chat = dialog.chat
        if chat.type == ChatType.PRIVATE:
            return "user"
        elif chat.type == ChatType.GROUP:
            return "group"
        elif chat.type == ChatType.SUPERGROUP:
            return "supergroup"
        elif chat.type == ChatType.CHANNEL:
            return "channel"
        return "unknown"

    def _get_contact_name(self, dialog: Dialog) -> str:
        chat = dialog.chat
        if chat.first_name:
            name = chat.first_name
            if chat.last_name:
                name += f" {chat.last_name}"
            return name
        elif chat.title:
            return chat.title
        return str(chat.id)
