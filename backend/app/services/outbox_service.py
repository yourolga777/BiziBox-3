import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..channels.base import BaseChannelAdapter
from ..config import settings
from ..models import OutboxMessageModel
from ..repositories.message import MessageRepository
from ..repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.repo = OutboxRepository(session, owner_id)
        self.message_repo = MessageRepository(session, owner_id)

    @staticmethod
    def _parse_attachments(
        raw: Optional[str],
    ) -> list[dict[str, Any]]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [a for a in parsed if isinstance(a, dict)]
        except (ValueError, TypeError):
            logger.warning("Bad outbox attachments JSON: %r", raw)
        return []

    async def enqueue(
        self,
        *,
        message_id: Optional[int],
        channel: str,
        channel_id: str,
        reply_to: Optional[str],
        content: str,
        subject: Optional[str] = None,
        client_request_id: Optional[str] = None,
        attachments: Optional[str] = None,
    ) -> OutboxMessageModel:
        if client_request_id:
            existing = await self.repo.get_by_client_request_id(client_request_id)
            if existing is not None:
                return existing
        return await self.repo.create(
            message_id=message_id,
            channel=channel,
            channel_id=channel_id,
            reply_to=reply_to,
            subject=subject,
            content=content,
            client_request_id=client_request_id,
            attachments=attachments,
            status="pending",
            attempts=0,
        )

    async def attempt_delivery(
        self,
        adapter: BaseChannelAdapter,
        record: OutboxMessageModel,
        max_attempts: int,
        base_delay: int,
    ) -> Optional[Dict[str, Any]]:
        """Пытается доставить одно сообщение.

        Возвращает словарь результата отправки при успехе (и помечает outbox как
        sent), либо None при неудаче (обновляет attempts/next_retry_at или failed).
        """
        channel_id: str = str(record.channel_id)
        content: str = str(record.content)
        reply_to: Optional[str] = str(record.reply_to) if record.reply_to else None
        subject: Optional[str] = str(record.subject) if record.subject else None

        try:
            attachments = self._parse_attachments(record.attachments)
            if attachments:
                result: Optional[Dict[str, Any]] = None
                for att in attachments:
                    file_path = att.get("file_path")
                    file_name = att.get("file_name") or "file"
                    mime_type = att.get("mime_type")
                    res = await asyncio.wait_for(
                        adapter.send_file(
                            channel_id=channel_id,
                            file_path=str(file_path),
                            file_name=str(file_name),
                            mime_type=str(mime_type) if mime_type else None,
                            reply_to=reply_to,
                            caption=content or None,
                            subject=subject,
                        ),
                        timeout=settings.OUTBOX_SEND_TIMEOUT,
                    )
                    if result is None and res and res.get("message_id"):
                        result = res
            else:
                result = await asyncio.wait_for(
                    adapter.send_message(
                        channel_id=channel_id,
                        text=content,
                        reply_to=reply_to,
                        subject=subject,
                    ),
                    timeout=settings.OUTBOX_SEND_TIMEOUT,
                )
        except Exception as e:
            await self._on_failure(record, max_attempts, base_delay, str(e))
            return None

        if result and result.get("message_id") and record.message_id:
            await self.message_repo.update(
                int(record.message_id),
                channel_message_id=str(result["message_id"]),
            )
        await self.repo.mark_sent(int(record.id))
        return result

    async def _on_failure(
        self,
        record: OutboxMessageModel,
        max_attempts: int,
        base_delay: int,
        error: str,
    ) -> None:
        attempts = int(record.attempts or 0) + 1
        if attempts >= max_attempts:
            logger.warning("Outbox %s failed after %d attempts: %s", record.id, attempts, error)
            await self.repo.mark_failed(int(record.id), error)
            return

        delay = base_delay * (2 ** (attempts - 1))
        next_retry_at = datetime.now() + timedelta(seconds=delay)
        await self.repo.schedule_retry(int(record.id), attempts, next_retry_at, error)

    async def process_pending(
        self,
        adapters: Dict[str, BaseChannelAdapter],
        max_attempts: int,
        base_delay: int,
        limit: int = 50,
    ) -> int:
        now = datetime.now()
        records = await self.repo.get_pending(now, limit)
        delivered = 0
        for record in records:
            adapter = adapters.get(str(record.channel))
            if not adapter:
                # Канал офлайн — оставляем pending, попробуем в следующем цикле.
                continue
            result = await self.attempt_delivery(adapter, record, max_attempts, base_delay)
            if result is not None:
                delivered += 1
        return delivered

    async def retry(
        self,
        outbox_id: int,
        adapters: Dict[str, BaseChannelAdapter],
        max_attempts: int,
        base_delay: int,
    ) -> Optional[OutboxMessageModel]:
        record = await self.repo.get_by_id(outbox_id)
        if not record:
            return None
        if record.status == "sent":
            return record

        # Не отправляем повторно, если сообщение уже было доставлено в канал
        # (ответ потерялся на границе, но channel_message_id уже проставлен).
        if record.message_id:
            msg = await self.message_repo.get_by_id(int(record.message_id))
            if msg is not None and msg.channel_message_id:
                await self.repo.mark_sent(int(record.id))
                return record

        adapter = adapters.get(str(record.channel))
        if not adapter:
            await self.repo.schedule_retry(
                int(record.id),
                int(record.attempts or 0),
                datetime.now(),
                str(record.last_error) if record.last_error else None,
            )
            return record

        record.attempts = 0
        await self.attempt_delivery(adapter, record, max_attempts, base_delay)
        return record
