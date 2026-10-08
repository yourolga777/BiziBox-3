import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..channels.base import BaseChannelAdapter
from ..config import settings
from ..paths import get_data_dir
from ..repositories.contact import ContactRepository
from ..repositories.message import MessageRepository
from ..schemas.message import AttachmentInput, MessageCreate, MessageResponse
from ..services.message_service import MessageService
from ..services.outbox_service import OutboxService

logger = logging.getLogger(__name__)


class ChannelMessageService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.message_service = MessageService(session, owner_id=owner_id)
        self.message_repo = MessageRepository(session, owner_id)
        self.contact_repo = ContactRepository(session, owner_id)
        self.channels: Dict[str, BaseChannelAdapter] = {}

    def register_channel(self, channel_type: str, adapter: BaseChannelAdapter) -> None:
        self.channels[channel_type] = adapter

    def get_channel(self, channel_type: str) -> Optional[BaseChannelAdapter]:
        return self.channels.get(channel_type)

    def get_all_channels(self) -> Dict[str, BaseChannelAdapter]:
        return dict(self.channels)

    async def process_incoming(
        self,
        raw_message: dict[str, Any],
        *,
        allow_spam: bool = False,
        allow_channels: bool = False,
    ) -> Optional[MessageResponse]:
        channel = raw_message.get("channel")
        contact_id = raw_message.get("contact_id")
        channel_message_id = raw_message.get("message_id")

        raw_direction = raw_message.get("direction") or "incoming"

        if channel_message_id:
            existing = await self.message_repo.get_by_channel_message(
                channel=str(channel),
                channel_message_id=channel_message_id,
            )
            if existing:
                if existing.direction != raw_direction:
                    updated = await self.message_repo.update(
                        int(existing.id),
                        direction=raw_direction,
                    )
                    if updated:
                        logger.debug(
                            "Direction fixed for %s/%s: %s -> %s",
                            channel,
                            channel_message_id,
                            existing.direction,
                            raw_direction,
                        )
                        return MessageResponse.model_validate(updated)
                logger.debug(
                    "Duplicate message skipped: %s/%s",
                    channel,
                    channel_message_id,
                )
                return MessageResponse.model_validate(existing)

        contact = await self.contact_repo.get_or_create(
            name=raw_message.get("contact_name", contact_id),
            channel=channel,
            channel_id=contact_id,
            telegram_username=raw_message.get("contact_username"),
        )

        if not allow_spam and contact.life_sphere == "spam":
            logger.debug("Skipping message from spam contact %s", contact.id)
            return None

        if getattr(contact, "is_blocked", False) is True:
            logger.debug("Skipping message from blocked contact %s", contact.id)
            return None

        if not allow_channels and await self._is_channel_contact(contact):
            logger.debug("Skipping message from channel contact %s", contact.id)
            return None

        if channel_message_id and raw_direction == "outgoing":
            # Гонка: исходящее уже ушло в канал, но outbox ещё не проставил
            # channel_message_id. Связываем с ожидающей отправки, а не дублируем.
            pending = await self.message_repo.get_pending_outgoing(
                contact_id=int(contact.id),
                channel=str(channel),
            )
            if pending is not None:
                logger.debug(
                    "Outgoing already pending, linking %s/%s to msg %s",
                    channel,
                    channel_message_id,
                    pending.id,
                )
                await self.message_repo.update(
                    int(pending.id),
                    channel_message_id=channel_message_id,
                )
                await self.session.commit()
                return MessageResponse.model_validate(pending)

        if channel == "telegram":
            if not contact.telegram_id:
                await self.contact_repo.update(int(contact.id), telegram_id=contact_id)
        elif channel == "email" and not contact.email:
            await self.contact_repo.update(int(contact.id), email=contact_id)
        elif channel == "vk" and not contact.vk_id:
            await self.contact_repo.update(int(contact.id), vk_id=contact_id)
        message_data = MessageCreate(
            contact_id=contact.id,
            channel=str(channel),
            channel_message_id=channel_message_id,
            reply_to=raw_message.get("reply_to"),
            subject=raw_message.get("subject"),
            content=raw_message["content"],
            direction=raw_direction,
            status=raw_message.get(
                "status", "read" if raw_direction == "outgoing" else "unread"
            ),
            created_at=raw_message.get("created_at"),
            attachments=raw_message.get("attachments"),
        )

        return await self.message_service.create(message_data)

    async def _is_channel_contact(self, contact: Any) -> bool:
        return getattr(contact, "life_sphere", None) == "channels"

    @staticmethod
    def _email_reply_subject(subject: Optional[str]) -> Optional[str]:
        if not subject:
            return None
        if subject.lower().startswith("re:"):
            return subject
        return f"Re: {subject}"

    async def _ensure_can_send(self, channel: str) -> None:
        """Блокирует отправку, если канал работает в режиме «только входящие»."""
        from ..deps import get_poll_service

        ps = get_poll_service()
        if ps is not None and ps.get_channel_mode(channel) == "incoming_only":
            raise HTTPException(
                403,
                f"Канал {channel} работает только на приём — отправка отключена",
            )

    async def send_reply(
        self,
        message_id: int,
        content: str,
        client_request_id: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> Optional[MessageResponse]:
        original = await self.message_repo.get_by_id(message_id)
        if not original:
            return None

        await self._ensure_can_send(str(original.channel))

        outbox = OutboxService(self.session, owner_id=self.owner_id)
        if client_request_id:
            existing = await outbox.repo.get_by_client_request_id(client_request_id)
            if existing is not None and existing.message_id:
                fresh = await self.message_repo.get_by_id(int(existing.message_id))
                if fresh is not None:
                    return MessageResponse.model_validate(fresh)

        adapter = self.channels.get(str(original.channel))
        if not adapter:
            from ..deps import get_poll_service
            ps = get_poll_service()
            if ps:
                adapter = ps.get_channel(str(original.channel))
        if not adapter:
            raise HTTPException(503, f"Канал {original.channel} не подключён")

        contact = await self.contact_repo.get_by_id(int(original.contact_id))
        channel_id = await self._resolve_channel_id(
            contact,
            str(original.channel),
            recipient,
            adapter,
            error_detail=f"Не удалось определить контакт (msg {message_id})",
        )

        reply_to: Optional[str] = (
            str(original.channel_message_id) if original.channel_message_id else None
        )
        subject: Optional[str] = None
        if original.channel == "email":
            subject = self._email_reply_subject(original.subject)

        reply_data = MessageCreate(
            contact_id=int(original.contact_id),
            channel=str(original.channel),
            channel_message_id=None,
            reply_to=reply_to,
            content=content,
            direction="outgoing",
            status="read",
        )

        reply = await self.message_service.create(reply_data)
        if client_request_id:
            await self.message_repo.update(
                int(reply.id), client_request_id=client_request_id
            )

        record = await outbox.enqueue(
            message_id=int(reply.id),
            channel=str(original.channel),
            channel_id=channel_id,
            reply_to=reply_to,
            content=content,
            subject=subject,
            client_request_id=client_request_id,
        )

        # Durability: фиксируем намерение доставки до сетевого вызова — при сбое
        # сообщение остаётся в outbox и не теряется.
        await self.session.commit()

        result = await outbox.attempt_delivery(
            adapter,
            record,
            settings.OUTBOX_MAX_ATTEMPTS,
            settings.OUTBOX_BASE_DELAY,
        )
        if result and result.get("message_id"):
            reply.channel_message_id = result["message_id"]

        await self.contact_repo.update(int(original.contact_id), is_known=True)
        await self.message_repo.update(message_id, status="read")

        return reply

    async def send_file_reply(
        self,
        message_id: int,
        files: list[UploadFile],
        content: str = "",
        client_request_id: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> Optional[MessageResponse]:
        original = await self.message_repo.get_by_id(message_id)
        if not original:
            return None

        await self._ensure_can_send(str(original.channel))

        outbox = OutboxService(self.session, owner_id=self.owner_id)
        if client_request_id:
            existing = await outbox.repo.get_by_client_request_id(client_request_id)
            if existing is not None and existing.message_id:
                fresh = await self.message_repo.get_by_id(int(existing.message_id))
                if fresh is not None:
                    return MessageResponse.model_validate(fresh)

        adapter = self.channels.get(str(original.channel))
        if not adapter:
            from ..deps import get_poll_service
            ps = get_poll_service()
            if ps:
                adapter = ps.get_channel(str(original.channel))
        if not adapter:
            raise HTTPException(503, f"Канал {original.channel} не подключён")

        contact = await self.contact_repo.get_by_id(int(original.contact_id))
        channel_id = await self._resolve_channel_id(
            contact,
            str(original.channel),
            recipient,
            adapter,
            error_detail=f"Не удалось определить контакт (msg {message_id})",
        )

        attachments_dir = get_data_dir() / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        attachment_dicts: list[dict[str, Any]] = []
        saved: list[tuple[str, str, str | None]] = []
        for f in files:
            data = await f.read()
            safe_name = os.path.basename(f.filename or "file") or "file"
            local_path = attachments_dir / f"{uuid.uuid4().hex}_{safe_name}"
            local_path.write_bytes(data)
            mime_type = getattr(f, "content_type", None) or None
            saved.append((str(local_path), safe_name, mime_type))
            attachment_dicts.append(
                {
                    "file_name": safe_name,
                    "file_size": len(data),
                    "mime_type": mime_type,
                    "file_path": str(local_path),
                }
            )

        reply_to: Optional[str] = (
            str(original.channel_message_id) if original.channel_message_id else None
        )
        subject: Optional[str] = None
        if original.channel == "email":
            subject = self._email_reply_subject(original.subject)

        reply_data = MessageCreate(
            contact_id=int(original.contact_id),
            channel=str(original.channel),
            channel_message_id=None,
            reply_to=reply_to,
            content=content or "",
            direction="outgoing",
            status="read",
            attachments=[AttachmentInput(**d) for d in attachment_dicts] if attachment_dicts else None,
        )

        reply = await self.message_service.create(reply_data)
        if client_request_id:
            await self.message_repo.update(
                int(reply.id), client_request_id=client_request_id
            )

        attachments_meta = [
            {
                "file_path": sp,
                "file_name": fn,
                "mime_type": mt,
            }
            for sp, fn, mt in saved
        ]
        record = await outbox.enqueue(
            message_id=int(reply.id),
            channel=str(original.channel),
            channel_id=channel_id,
            reply_to=reply_to,
            content=content or "",
            subject=subject,
            client_request_id=client_request_id,
            attachments=json.dumps(attachments_meta, ensure_ascii=False),
        )
        await self.session.commit()

        result = await outbox.attempt_delivery(
            adapter,
            record,
            settings.OUTBOX_MAX_ATTEMPTS,
            settings.OUTBOX_BASE_DELAY,
        )
        if result and result.get("message_id"):
            await self.message_repo.update(
                int(reply.id), channel_message_id=str(result["message_id"])
            )

        await self.contact_repo.update(int(original.contact_id), is_known=True)
        await self.message_repo.update(message_id, status="read")
        await self.session.commit()

        fresh = await self.message_repo.get_by_id(int(reply.id))
        if fresh is not None:
            return MessageResponse.model_validate(fresh)
        return reply

    async def _resolve_adapter(self, channel: str) -> BaseChannelAdapter:
        adapter = self.channels.get(channel)
        if not adapter:
            from ..deps import get_poll_service
            ps = get_poll_service()
            if ps:
                adapter = ps.get_channel(channel)
        if not adapter:
            raise HTTPException(503, f"Канал {channel} не подключён")
        return adapter

    async def _resolve_channel_id(
        self,
        contact: Any,
        channel: str,
        recipient: Optional[str] = None,
        adapter: Any = None,
        error_detail: str = "Не удалось определить адрес контакта",
    ) -> str:
        if recipient and recipient.strip():
            value = recipient.strip()
            if channel == "telegram" and not value.isdigit():
                if adapter is None:
                    raise HTTPException(400, error_detail)
                try:
                    resolved = await adapter.resolve_channel_id(value)
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(400, error_detail)
                if not resolved:
                    raise HTTPException(400, error_detail)
                return str(resolved)
            return value
        if channel == "telegram":
            channel_id = str(contact.telegram_id) if contact and contact.telegram_id else None
        elif channel == "email":
            channel_id = str(contact.email) if contact and contact.email else None
        elif channel == "vk":
            channel_id = str(contact.vk_id) if contact and contact.vk_id else None
        else:
            channel_id = None
        if not channel_id:
            raise HTTPException(400, error_detail)
        return channel_id

    async def send_message(
        self,
        contact_id: int,
        channel: str,
        content: str,
        client_request_id: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> Optional[MessageResponse]:
        await self._ensure_can_send(channel)
        outbox = OutboxService(self.session, owner_id=self.owner_id)
        if client_request_id:
            existing = await outbox.repo.get_by_client_request_id(client_request_id)
            if existing is not None and existing.message_id:
                fresh = await self.message_repo.get_by_id(int(existing.message_id))
                if fresh is not None:
                    return MessageResponse.model_validate(fresh)

        adapter = await self._resolve_adapter(channel)
        contact = await self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise HTTPException(404, "Контакт не найден")
        channel_id = await self._resolve_channel_id(contact, channel, recipient, adapter)

        reply_data = MessageCreate(
            contact_id=contact_id,
            channel=channel,
            channel_message_id=None,
            reply_to=None,
            content=content,
            direction="outgoing",
            status="read",
        )
        reply = await self.message_service.create(reply_data)
        if client_request_id:
            await self.message_repo.update(int(reply.id), client_request_id=client_request_id)

        record = await outbox.enqueue(
            message_id=int(reply.id),
            channel=channel,
            channel_id=channel_id,
            reply_to=None,
            content=content,
            client_request_id=client_request_id,
        )
        await self.session.commit()

        result = await outbox.attempt_delivery(
            adapter,
            record,
            settings.OUTBOX_MAX_ATTEMPTS,
            settings.OUTBOX_BASE_DELAY,
        )
        if result and result.get("message_id"):
            await self.message_repo.update(int(reply.id), channel_message_id=str(result["message_id"]))

        await self.contact_repo.update(contact_id, is_known=True)
        await self.session.commit()

        fresh = await self.message_repo.get_by_id(int(reply.id))
        if fresh is not None:
            return MessageResponse.model_validate(fresh)
        return reply

    async def send_file_message(
        self,
        contact_id: int,
        channel: str,
        files: list[UploadFile],
        content: str = "",
        client_request_id: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> Optional[MessageResponse]:
        await self._ensure_can_send(channel)
        outbox = OutboxService(self.session, owner_id=self.owner_id)
        if client_request_id:
            existing = await outbox.repo.get_by_client_request_id(client_request_id)
            if existing is not None and existing.message_id:
                fresh = await self.message_repo.get_by_id(int(existing.message_id))
                if fresh is not None:
                    return MessageResponse.model_validate(fresh)

        adapter = await self._resolve_adapter(channel)
        contact = await self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise HTTPException(404, "Контакт не найден")
        channel_id = await self._resolve_channel_id(contact, channel, recipient, adapter)

        attachments_dir = get_data_dir() / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        attachment_dicts: list[dict[str, Any]] = []
        saved: list[tuple[str, str, str | None]] = []
        for f in files:
            data = await f.read()
            safe_name = os.path.basename(f.filename or "file") or "file"
            local_path = attachments_dir / f"{uuid.uuid4().hex}_{safe_name}"
            local_path.write_bytes(data)
            mime_type = getattr(f, "content_type", None) or None
            saved.append((str(local_path), safe_name, mime_type))
            attachment_dicts.append(
                {
                    "file_name": safe_name,
                    "file_size": len(data),
                    "mime_type": mime_type,
                    "file_path": str(local_path),
                }
            )

        reply_data = MessageCreate(
            contact_id=contact_id,
            channel=channel,
            channel_message_id=None,
            reply_to=None,
            content=content or "",
            direction="outgoing",
            status="read",
            attachments=[AttachmentInput(**d) for d in attachment_dicts] if attachment_dicts else None,
        )
        reply = await self.message_service.create(reply_data)
        if client_request_id:
            await self.message_repo.update(int(reply.id), client_request_id=client_request_id)

        attachments_meta = [
            {"file_path": sp, "file_name": fn, "mime_type": mt}
            for sp, fn, mt in saved
        ]
        record = await outbox.enqueue(
            message_id=int(reply.id),
            channel=channel,
            channel_id=channel_id,
            reply_to=None,
            content=content or "",
            client_request_id=client_request_id,
            attachments=json.dumps(attachments_meta, ensure_ascii=False),
        )
        await self.session.commit()

        result = await outbox.attempt_delivery(
            adapter,
            record,
            settings.OUTBOX_MAX_ATTEMPTS,
            settings.OUTBOX_BASE_DELAY,
        )
        if result and result.get("message_id"):
            await self.message_repo.update(int(reply.id), channel_message_id=str(result["message_id"]))

        await self.contact_repo.update(contact_id, is_known=True)
        await self.session.commit()

        fresh = await self.message_repo.get_by_id(int(reply.id))
        if fresh is not None:
            return MessageResponse.model_validate(fresh)
        return reply

    async def get_conversation(
        self,
        contact_id: int,
        limit: int = 100,
    ) -> List[MessageResponse]:
        return await self.message_service.get_dialog(contact_id, limit=limit)

    async def send_to_recipient(
        self,
        channel: str,
        recipient: str,
        content: str,
        client_request_id: Optional[str] = None,
    ) -> MessageResponse:
        await self._ensure_can_send(channel)
        adapter = self.channels.get(channel)
        if not adapter:
            raise HTTPException(503, f"Канал {channel} не подключён")

        clean_recipient = (recipient or "").strip().lstrip("@")
        if not clean_recipient:
            raise HTTPException(400, "Получатель не указан")

        channel_id = await adapter.resolve_channel_id(clean_recipient)

        contact = await self.contact_repo.get_or_create(
            name=clean_recipient,
            channel=channel,
            channel_id=channel_id,
        )

        outbox = OutboxService(self.session, owner_id=self.owner_id)
        if client_request_id:
            existing = await outbox.repo.get_by_client_request_id(client_request_id)
            if existing is not None and existing.message_id:
                fresh = await self.message_repo.get_by_id(int(existing.message_id))
                if fresh is not None:
                    return MessageResponse.model_validate(fresh)

        reply_data = MessageCreate(
            contact_id=int(contact.id),
            channel=channel,
            channel_message_id=None,
            content=content,
            direction="outgoing",
            status="read",
        )
        reply = await self.message_service.create(reply_data)
        if client_request_id:
            await self.message_repo.update(
                int(reply.id), client_request_id=client_request_id
            )

        subject: Optional[str] = None
        if channel == "email" and content:
            subject = content.splitlines()[0][:200] or None

        record = await outbox.enqueue(
            message_id=int(reply.id),
            channel=channel,
            channel_id=channel_id,
            reply_to=None,
            content=content,
            subject=subject,
            client_request_id=client_request_id,
        )
        await self.session.commit()

        result = await outbox.attempt_delivery(
            adapter,
            record,
            settings.OUTBOX_MAX_ATTEMPTS,
            settings.OUTBOX_BASE_DELAY,
        )
        if result and result.get("message_id"):
            await self.message_repo.update(
                int(reply.id), channel_message_id=str(result["message_id"])
            )
        await self.contact_repo.update(int(contact.id), is_known=True)
        await self.session.commit()

        fresh = await self.message_repo.get_by_id(int(reply.id))
        if fresh is not None:
            return MessageResponse.model_validate(fresh)
        return reply

    async def disconnect_all(self) -> None:
        for channel_type, adapter in self.channels.items():
            try:
                await adapter.disconnect()
                logger.info(f"Disconnected channel: {channel_type}")
            except Exception as e:
                logger.error(f"Error disconnecting {channel_type}: {e}")
        self.channels.clear()
