from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MessageAttachmentModel
from .base import BaseRepository


class AttachmentRepository(BaseRepository[MessageAttachmentModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(MessageAttachmentModel, session)

    async def get_by_message_id(self, message_id: int) -> list[MessageAttachmentModel]:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.message_id == message_id)
            .order_by(self.model.id)
        )
        return list(result.scalars().all())

    async def get_for_message(
        self, attachment_id: int, message_id: int
    ) -> Optional[MessageAttachmentModel]:
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == attachment_id,
                self.model.message_id == message_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_from_dicts(
        self, message_id: int, attachments: list[dict[str, Any]]
    ) -> list[MessageAttachmentModel]:
        created = []
        for att in attachments:
            created.append(
                await self.create(
                    message_id=message_id,
                    channel_message_id=att.get("channel_message_id"),
                    file_name=att.get("file_name"),
                    file_size=att.get("file_size"),
                    mime_type=att.get("mime_type"),
                    file_path=att.get("file_path"),
                )
            )
        return created
