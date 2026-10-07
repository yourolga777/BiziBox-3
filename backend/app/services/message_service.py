from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from ..config import DEFAULT_OWNER_ID
from ..models import ContactModel, MessageModel
from ..repositories.attachment import AttachmentRepository
from ..repositories.contact import ContactRepository
from ..repositories.contact_folder import ContactFolderRepository
from ..repositories.message import MessageRepository
from ..schemas.message import MessageCreate, MessageResponse, MessageUpdate, ThreadResponse
from ..utils.autolink import autolink
from ..utils.fts import index_message, reindex_message, search_message_ids
from ..utils.search import like_predicate, search_variants
from .otp import extract_otp


class MessageService:
    def __init__(
        self,
        session: AsyncSession,
        owner_id: Optional[int] = None,
    ):
        self.session = session
        self.owner_id = owner_id
        self.message_repo = MessageRepository(session, owner_id)
        self.contact_repo = ContactRepository(session, owner_id)

    async def _load_with_contact(self, model: MessageModel) -> MessageResponse:
        resp = MessageResponse.model_validate(model)
        resp.content_html = autolink(model.content)
        if model.contact_id:
            contact = await self.contact_repo.get_by_id(model.contact_id)
            if contact:
                resp.contact_name = contact.name
                resp.contact_username = contact.telegram_username
                if await self._is_service_contact(contact):
                    resp.extracted_code = extract_otp(model.content)
        return resp

    async def _is_service_contact(self, contact: ContactModel) -> bool:
        if contact.folder_id is None:
            return False
        folder_repo = ContactFolderRepository(self.session, self.owner_id)
        folder = await folder_repo.get_by_id(int(contact.folder_id))
        return bool(folder and folder.category_key == "service")

    async def get_all(
        self,
        contact_id: Optional[int] = None,
        channel: Optional[str] = None,
        unread: bool = False,
        flagged: bool = False,
        skip: int = 0,
        limit: int = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
        exclude_spam: bool = False,
        life_sphere: Optional[str] = None,
        folder_id: Optional[int] = None,
    ) -> List[MessageResponse]:
        messages = await self.message_repo.get_all(
            contact_id=contact_id,
            channel=channel,
            unread=unread,
            flagged=flagged,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            min_id=min_id,
            exclude_spam=exclude_spam,
            life_sphere=life_sphere,
            folder_id=folder_id,
        )
        return [await self._load_with_contact(m) for m in messages]

    async def get_by_scope(
        self,
        scope: str,
        skip: int = 0,
        limit: int = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
    ) -> List[MessageResponse]:
        messages = await self.message_repo.get_by_scope(
            scope=scope,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            min_id=min_id,
        )
        return [await self._load_with_contact(m) for m in messages]

    async def get_spam(
        self,
        skip: int = 0,
        limit: int = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
    ) -> List[MessageResponse]:
        messages = await self.message_repo.get_spam(
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            min_id=min_id,
        )
        return [await self._load_with_contact(m) for m in messages]

    async def get_threads(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[ThreadResponse]:
        latest = await self.message_repo.get_latest_by_contact(
            skip=skip, limit=limit
        )
        contact_ids = [int(m.contact_id) for m in latest]
        unread = await self.message_repo.get_unread_counts(contact_ids)
        channels = await self.message_repo.get_channels_by_contact(contact_ids)

        threads: List[ThreadResponse] = []
        for m in latest:
            cid = int(m.contact_id)
            threads.append(
                ThreadResponse(
                    contact_id=cid,
                    last_message=await self._load_with_contact(m),
                    unread_count=unread.get(cid, 0),
                    channels=channels.get(cid, []),
                )
            )
        return threads

    async def count_unread_spam(self) -> int:
        return await self.message_repo.count_unread_spam()

    async def cleanup_spam(self) -> int:
        return await self.message_repo.delete_spam()

    async def get_by_id(self, message_id: int) -> Optional[MessageResponse]:
        message = await self.message_repo.get_by_id(message_id)
        return await self._load_with_contact(message) if message else None

    async def search(self, q: str, limit: int = 200) -> List[MessageResponse]:
        owner_id = self.owner_id or DEFAULT_OWNER_ID
        variants = search_variants(q)

        content_ids: set[int] = set()
        for variant in variants:
            ids = await search_message_ids(self.session, variant, owner_id, limit)
            content_ids.update(ids)

        # Поиск по имени контакта (только имя, с транслитерацией Barinov ↔ Баринов).
        name_ids: set[int] = set()
        name_predicates = [like_predicate(ContactModel.name, v) for v in variants]
        query = select(ContactModel).where(
            or_(*name_predicates), ContactModel.deleted_at.is_(None)
        )
        if self.owner_id is not None:
            query = query.where(ContactModel.owner_id == self.owner_id)
        result = await self.session.execute(query.limit(100))
        contacts = list(result.scalars().all())
        if contacts:
            cids = [int(c.id) for c in contacts if c.id is not None]
            msgs = await self.message_repo.get_by_contacts(cids, limit)
            name_ids = {int(m.id) for m in msgs}

        all_ids = sorted(content_ids | name_ids, reverse=True)[:limit]
        if not all_ids:
            return []
        messages = await self.message_repo.get_by_ids(all_ids)
        return [await self._load_with_contact(m) for m in messages]

    async def create(self, data: MessageCreate) -> MessageResponse:
        if data.contact_id:
            contact = await self.contact_repo.get_by_id(data.contact_id)
            if not contact:
                contact = await self.contact_repo.create()
        else:
            contact = await self.contact_repo.get_or_create(
                channel=data.channel,
            )
            data.contact_id = int(contact.id)

        payload = data.model_dump(exclude_unset=True)
        attachment_dicts = payload.pop("attachments", None) or []

        message = await self.message_repo.create(**payload)
        await index_message(
            self.session,
            int(message.id),
            int(message.owner_id or DEFAULT_OWNER_ID),
            str(message.content or ""),
        )
        if attachment_dicts:
            attachment_repo = AttachmentRepository(self.session)
            created = await attachment_repo.create_from_dicts(
                int(message.id), attachment_dicts
            )
            set_committed_value(message, "attachments", created)  # type: ignore[no-untyped-call]
        else:
            set_committed_value(message, "attachments", [])  # type: ignore[no-untyped-call]

        resp = MessageResponse.model_validate(message)
        resp.content_html = autolink(message.content)
        return resp

    async def update(
        self, message_id: int, data: MessageUpdate
    ) -> Optional[MessageResponse]:
        payload = data.model_dump(exclude_unset=True)
        message = await self.message_repo.update(message_id, **payload)
        if message is not None and "content" in payload:
            await reindex_message(
                self.session,
                int(message.id),
                int(message.owner_id or DEFAULT_OWNER_ID),
                str(message.content or ""),
            )
        if message is None:
            return None
        resp = MessageResponse.model_validate(message)
        resp.content_html = autolink(message.content)
        return resp

    async def snooze(
        self, message_id: int, until: datetime
    ) -> Optional[MessageResponse]:
        message = await self.message_repo.update(message_id, snoozed_until=until)
        if message is None:
            return None
        resp = MessageResponse.model_validate(message)
        resp.content_html = autolink(message.content)
        return resp

    async def delete(self, message_id: int) -> bool:
        return await self.message_repo.bulk_soft_delete([message_id]) > 0

    async def delete_contact_messages(self, contact_id: int) -> int:
        messages = await self.message_repo.get_all(contact_id=contact_id, limit=10000)
        ids = [int(m.id) for m in messages]
        if not ids:
            return 0
        return await self.message_repo.bulk_soft_delete(ids)

    async def mark_contact_unread(self, contact_id: int) -> bool:
        messages = await self.message_repo.get_all(contact_id=contact_id, limit=1)
        if not messages:
            return False
        await self.message_repo.update(int(messages[0].id), status="unread")
        return True

    async def mark_contact_read(self, contact_id: int) -> int:
        return await self.message_repo.mark_contact_read(contact_id)

    async def bulk_update_status(self, ids: list[int], status: str) -> int:
        return await self.message_repo.bulk_update_status(ids, status)

    async def bulk_delete(self, ids: list[int]) -> int:
        return await self.message_repo.bulk_soft_delete(ids)

    async def bulk_restore(self, ids: list[int]) -> int:
        return await self.message_repo.bulk_restore(ids)

    async def get_dialog(
        self,
        contact_id: int,
        limit: int = 200,
        before_created_at: Optional[datetime] = None,
        before_id: Optional[int] = None,
    ) -> List[MessageResponse]:
        messages = await self.message_repo.get_by_contact(
            contact_id,
            limit=limit,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        return [await self._load_with_contact(m) for m in messages]

