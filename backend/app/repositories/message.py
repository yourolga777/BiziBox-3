from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import MessageModel
from .base import BaseRepository


class MessageRepository(BaseRepository[MessageModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(MessageModel, session, owner_id)

    async def get_by_id(self, id: int) -> Optional[MessageModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.id == id)
                .options(selectinload(self.model.attachments))
            )
        )
        return result.scalar_one_or_none()

    async def get_all(  # type: ignore[override]
        self,
        contact_id: Optional[int] = None,
        channel: Optional[str] = None,
        unread: bool = False,
        flagged: bool = False,
        skip: int = 0,
        limit: Optional[int] = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
        exclude_spam: bool = False,
        life_sphere: Optional[str] = None,
        folder_id: Optional[int] = None,
    ) -> List[MessageModel]:
        from ..models.contact import ContactModel

        query = self._scoped(select(self.model))
        if exclude_spam or life_sphere or folder_id is not None:
            query = query.join(
                ContactModel, self.model.contact_id == ContactModel.id
            )
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        if exclude_spam:
            query = query.where(
                or_(
                    ContactModel.life_sphere.is_(None),
                    ContactModel.life_sphere != "spam",
                )
            )
        if life_sphere:
            query = query.where(ContactModel.life_sphere == life_sphere)
        if folder_id is not None:
            query = query.where(ContactModel.folder_id == folder_id)
        if min_id is not None:
            query = query.where(self.model.id > min_id)
        if contact_id:
            query = query.where(self.model.contact_id == contact_id)
        if channel:
            query = query.where(self.model.channel == channel)
        if unread:
            query = query.where(self.model.status == "unread")
            query = query.where(
                or_(
                    self.model.snoozed_until.is_(None),
                    self.model.snoozed_until <= datetime.now(),
                )
            )
        if flagged:
            query = query.where(self.model.is_flagged.is_(True))
        query = query.order_by(self.model.created_at.desc())
        query = query.options(selectinload(self.model.attachments), selectinload(self.model.contact))
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_by_contact(
        self,
        contact_id: int,
        limit: int = 200,
        before_created_at: Optional[datetime] = None,
        before_id: Optional[int] = None,
    ) -> List[MessageModel]:
        query = (
            self._scoped(select(self.model).where(self.model.contact_id == contact_id))
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .options(selectinload(self.model.attachments), selectinload(self.model.contact))
        )
        if before_created_at is not None:
            if before_id is not None:
                query = query.where(
                    or_(
                        self.model.created_at < before_created_at,
                        and_(
                            self.model.created_at == before_created_at,
                            self.model.id < before_id,
                        ),
                    )
                )
            else:
                query = query.where(self.model.created_at < before_created_at)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_oldest_by_contact(
        self, contact_id: int
    ) -> Optional[MessageModel]:
        """Возвращает самое старое сообщение контакта (для offset при загрузке предыдущих)."""
        query = self._scoped(
            select(self.model)
            .where(
                self.model.contact_id == contact_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.created_at.asc(), self.model.id.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[int]) -> List[MessageModel]:
        if not ids:
            return []
        query = self._scoped(
            select(self.model)
            .where(self.model.id.in_(ids), self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .options(selectinload(self.model.attachments), selectinload(self.model.contact))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_contacts(self, contact_ids: List[int], limit: int = 200) -> List[MessageModel]:
        if not contact_ids:
            return []
        query = self._scoped(
            select(self.model)
            .where(
                self.model.contact_id.in_(contact_ids),
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .options(selectinload(self.model.attachments), selectinload(self.model.contact))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_channel(self, channel: str) -> List[MessageModel]:
        return await self.get_all(channel=channel)

    async def get_unread(self) -> List[MessageModel]:
        return await self.get_all(unread=True)

    async def get_by_channel_message(
        self, channel: str, channel_message_id: str
    ) -> Optional[MessageModel]:
        query = self._scoped(
            select(self.model).where(
                self.model.channel == channel,
                self.model.channel_message_id == channel_message_id,
                self.model.deleted_at.is_(None),
            ).options(selectinload(self.model.attachments))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_outgoing(
        self,
        *,
        contact_id: int,
        channel: str,
        window_minutes: int = 60,
    ) -> Optional[MessageModel]:
        from datetime import timedelta

        query = (
            self._scoped(
                select(self.model).where(
                    self.model.contact_id == contact_id,
                    self.model.channel == channel,
                    self.model.direction == "outgoing",
                    self.model.channel_message_id.is_(None),
                    self.model.deleted_at.is_(None),
                    self.model.created_at
                    >= datetime.now() - timedelta(minutes=window_minutes),
                )
            )
            .order_by(self.model.created_at.desc())
            .options(selectinload(self.model.attachments))
        )
        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_by_scope(
        self,
        scope: str,
        skip: int = 0,
        limit: int = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
    ) -> List[MessageModel]:
        from ..models.contact import ContactModel

        query = self._scoped(
            select(self.model)
            .join(ContactModel, self.model.contact_id == ContactModel.id)
            .order_by(self.model.created_at.desc())
        )
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        if min_id is not None:
            query = query.where(self.model.id > min_id)

        query = query.where(
            or_(
                ContactModel.life_sphere.is_(None),
                ContactModel.life_sphere != "spam",
            )
        )

        query = query.options(selectinload(self.model.attachments))
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_latest_by_contact(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[MessageModel]:
        """Последнее сообщение на каждый контакт (по created_at desc, id desc).

        Исключает спам-контакты и удалённые сообщения/контакты. Возвращает
        сообщения, отсортированные по дате последнего сообщения контакта.
        """
        from ..models.contact import ContactModel

        rn = func.row_number().over(
            partition_by=MessageModel.contact_id,
            order_by=(MessageModel.created_at.desc(), MessageModel.id.desc()),
        ).label("rn")

        inner = select(MessageModel.id.label("id"), rn).where(
            MessageModel.deleted_at.is_(None)
        )
        if self.owner_id is not None:
            inner = inner.where(MessageModel.owner_id == self.owner_id)
        sub = inner.subquery()

        query = (
            select(MessageModel)
            .join(sub, sub.c.id == MessageModel.id)
            .join(ContactModel, MessageModel.contact_id == ContactModel.id)
            .where(sub.c.rn == 1)
            .where(
                or_(
                    ContactModel.life_sphere.is_(None),
                    ContactModel.life_sphere != "spam",
                )
            )
            .where(ContactModel.deleted_at.is_(None))
            .order_by(MessageModel.created_at.desc(), MessageModel.id.desc())
            .options(
                selectinload(MessageModel.attachments),
                selectinload(MessageModel.contact),
            )
        )
        query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_unread_counts(self, contact_ids: List[int]) -> dict[int, int]:
        if not contact_ids:
            return {}
        query = (
            select(MessageModel.contact_id, func.count())
            .where(
                MessageModel.contact_id.in_(contact_ids),
                MessageModel.status == "unread",
                MessageModel.deleted_at.is_(None),
            )
            .group_by(MessageModel.contact_id)
        )
        if self.owner_id is not None:
            query = query.where(MessageModel.owner_id == self.owner_id)
        result = await self.session.execute(query)
        return {int(r[0]): int(r[1]) for r in result.all()}

    async def get_channels_by_contact(
        self, contact_ids: List[int]
    ) -> dict[int, list[str]]:
        if not contact_ids:
            return {}
        query = (
            select(MessageModel.contact_id, MessageModel.channel)
            .where(
                MessageModel.contact_id.in_(contact_ids),
                MessageModel.deleted_at.is_(None),
            )
            .distinct()
        )
        if self.owner_id is not None:
            query = query.where(MessageModel.owner_id == self.owner_id)
        result = await self.session.execute(query)
        out: dict[int, list[str]] = {}
        for cid, channel in result.all():
            out.setdefault(int(cid), []).append(str(channel))
        return out

    async def get_spam(
        self,
        skip: int = 0,
        limit: int = 200,
        include_deleted: bool = False,
        min_id: Optional[int] = None,
    ) -> List[MessageModel]:
        from ..models.contact import ContactModel

        query = self._scoped(
            select(self.model)
            .join(ContactModel, self.model.contact_id == ContactModel.id)
            .where(ContactModel.life_sphere == "spam")
            .order_by(self.model.created_at.desc())
        )
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        if min_id is not None:
            query = query.where(self.model.id > min_id)

        query = query.options(selectinload(self.model.attachments))
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count_unread_spam(self) -> int:
        from ..models.contact import ContactModel

        query = self._scoped(
            select(func.count())
            .select_from(self.model)
            .join(ContactModel, self.model.contact_id == ContactModel.id)
            .where(
                ContactModel.life_sphere == "spam",
                self.model.status == "unread",
                self.model.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        return int(result.scalar() or 0)

    async def delete_spam(self) -> int:
        """Soft-delete все сообщения спам-контактов (life_sphere=spam)."""
        from ..models.contact import ContactModel

        spam_ids = select(ContactModel.id).where(
            ContactModel.life_sphere == "spam"
        )
        stmt = (
            sql_update(MessageModel)
            .where(MessageModel.contact_id.in_(spam_ids))
            .where(MessageModel.deleted_at.is_(None))
            .values(deleted_at=datetime.now())
        )
        if self.owner_id is not None:
            stmt = stmt.where(MessageModel.owner_id == self.owner_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def bulk_update_status(
        self, ids: list[int], status: str
    ) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(MessageModel)
                .where(MessageModel.id.in_(ids))
                .where(MessageModel.deleted_at.is_(None))
                .values(status=status)
            )
        )
        await self.session.flush()
        return result.rowcount

    async def mark_contact_read(self, contact_id: int) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(MessageModel)
                .where(MessageModel.contact_id == contact_id)
                .where(MessageModel.status == "unread")
                .where(MessageModel.deleted_at.is_(None))
                .values(status="read")
            )
        )
        await self.session.flush()
        return result.rowcount

    async def bulk_soft_delete(self, ids: list[int]) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(MessageModel)
                .where(MessageModel.id.in_(ids))
                .where(MessageModel.deleted_at.is_(None))
                .values(deleted_at=datetime.now())
            )
        )
        await self.session.flush()
        return result.rowcount

    async def bulk_restore(self, ids: list[int]) -> int:
        result = await self.session.execute(
            self._scoped(
                sql_update(MessageModel)
                .where(MessageModel.id.in_(ids))
                .where(MessageModel.deleted_at.is_not(None))
                .values(deleted_at=None)
            )
        )
        await self.session.flush()
        return result.rowcount

