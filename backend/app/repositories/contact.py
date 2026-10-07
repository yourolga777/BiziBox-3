from typing import Any, List, Optional

from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    ContactModel,
    ContactTypeTemplateModel,
    MessageModel,
    TaskModel,
    contact_contact_type_association,
)
from ..utils.search import like_predicate, phone_search_predicates, search_variants
from .base import BaseRepository


class ContactRepository(BaseRepository[ContactModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(ContactModel, session, owner_id)

    async def get_all(  # type: ignore[override]
        self,
        search: Optional[str] = None,
        channel: Optional[str] = None,
        subsection: Optional[str] = None,
        life_sphere: Optional[str] = None,
        contact_type_ids: Optional[List[int]] = None,
        folder_ids: Optional[List[int]] = None,
        is_favorite: Optional[bool] = None,
        unclassified: bool = False,
        sort_by: str = "name",
        sort_order: str = "asc",
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[ContactModel]:
        query = self._scoped(select(self.model).where(self.model.deleted_at.is_(None)))

        if search:
            search_predicates: list[Any] = []
            for variant in search_variants(search):
                search_predicates.extend(
                    [
                        like_predicate(self.model.name, variant),
                        like_predicate(self.model.phone, variant),
                        like_predicate(self.model.email, variant),
                        like_predicate(self.model.telegram_username, variant),
                        like_predicate(self.model.telegram_id, variant),
                        self.model.id.in_(
                            select(MessageModel.contact_id)
                            .where(
                                like_predicate(MessageModel.content, variant),
                                MessageModel.deleted_at.is_(None),
                            )
                            .limit(1000),
                        ),
                    ]
                )
            search_predicates.extend(phone_search_predicates(self.model.phone, search))
            query = query.where(or_(*search_predicates))

        if channel == "telegram":
            query = query.where(self.model.telegram_id.is_not(None))
        elif channel == "email":
            query = query.where(self.model.email.is_not(None))
        elif channel == "vk":
            query = query.where(self.model.vk_id.is_not(None))

        if subsection == "new":
            query = query.where(self.model.is_known.is_(False))

        if life_sphere:
            query = query.where(self.model.life_sphere == life_sphere)

        if contact_type_ids:
            query = query.where(
                self.model.id.in_(
                    select(contact_contact_type_association.c.contact_id).where(
                        contact_contact_type_association.c.template_id.in_(
                            contact_type_ids
                        ),
                        contact_contact_type_association.c.owner_id
                        == self.owner_id,
                    )
                )
            )

        if folder_ids is not None:
            query = query.where(self.model.folder_id.in_(folder_ids))

        if unclassified:
            query = query.where(
                self.model.life_sphere.is_(None),
                self.model.folder_id.is_(None),
            )

        if is_favorite is not None:
            query = query.where(self.model.is_favorite.is_(is_favorite))

        desc_order = sort_order == "desc"
        if sort_by == "created_at":
            col = self.model.created_at
            query = query.order_by(desc(col) if desc_order else col)
        elif sort_by == "message_count":
            msg_count = (
                select(func.count())
                .where(MessageModel.contact_id == self.model.id)
                .correlate(self.model)
                .scalar_subquery()
            )
            query = query.order_by(desc(msg_count) if desc_order else msg_count)
        elif sort_by == "last_activity":
            last_act = (
                select(func.max(MessageModel.created_at))
                .where(MessageModel.contact_id == self.model.id)
                .correlate(self.model)
                .scalar_subquery()
            )
            query = query.order_by(
                desc(func.coalesce(last_act, text("'1970-01-01'")))
                if desc_order
                else func.coalesce(last_act, text("'1970-01-01'"))
            )
        elif sort_by == "first_message":
            first_msg = (
                select(func.min(MessageModel.created_at))
                .where(MessageModel.contact_id == self.model.id)
                .correlate(self.model)
                .scalar_subquery()
            )
            query = query.order_by(
                desc(func.coalesce(first_msg, text("'1970-01-01'")))
                if desc_order
                else func.coalesce(first_msg, text("'1970-01-01'"))
            )
        elif sort_by == "has_tasks":
            task_count = (
                select(func.count())
                .where(TaskModel.contact_id == self.model.id)
                .correlate(self.model)
                .scalar_subquery()
            )
            query = query.order_by(desc(task_count) if desc_order else task_count)
        else:
            query = query.order_by(
                desc(self.model.name) if desc_order else self.model.name
            )

        query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_deleted(
        self, skip: int = 0, limit: int = 100
    ) -> List[ContactModel]:
        query = self._scoped(
            select(self.model)
            .where(self.model.deleted_at.is_not(None))
            .order_by(self.model.deleted_at.desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def search(self, query: str) -> List[ContactModel]:
        return await self.get_all(search=query)

    async def get_or_create(
        self,
        name: Optional[str] = None,
        channel: Optional[str] = None,
        channel_id: Optional[str] = None,
        telegram_username: Optional[str] = None,
    ) -> "ContactModel":
        if channel == "telegram" and channel_id:
            existing = await self.get_by_telegram_id(channel_id)
            if existing:
                if existing.deleted_at is not None:
                    existing = await self.restore(existing.id)
                if existing:
                    updates: dict[str, Any] = {}
                    if (
                        telegram_username
                        and existing.telegram_username != telegram_username
                    ):
                        updates["telegram_username"] = telegram_username
                    if name and (
                        not existing.name
                        or existing.name.startswith("Контакт")
                        or existing.name == channel_id
                    ):
                        updates["name"] = name
                    if updates:
                        await self.update(existing.id, **updates)
                    return existing

        if channel == "email" and channel_id:
            existing = await self.get_by_email(channel_id)
            if existing:
                if existing.deleted_at is not None:
                    existing = await self.restore(existing.id)
            if existing:
                email_updates: dict[str, Any] = {}
                if name and (
                    not existing.name
                    or existing.name.startswith("Контакт")
                    or existing.name == channel_id
                    or "@" in existing.name
                ):
                    email_updates["name"] = name
                if email_updates:
                    await self.update(existing.id, **email_updates)
                return existing

        if channel == "vk" and channel_id:
            existing = await self.get_by_vk_id(channel_id)
            if existing:
                if existing.deleted_at is not None:
                    existing = await self.restore(existing.id)
            if existing:
                vk_updates: dict[str, Any] = {}
                if name and (
                    not existing.name
                    or existing.name.startswith("Контакт")
                    or existing.name == channel_id
                ):
                    vk_updates["name"] = name
                if vk_updates:
                    await self.update(existing.id, **vk_updates)
                return existing

        kwargs: dict[str, Any] = {
            "name": name or f"Контакт ({channel or 'unknown'})",
        }
        if channel == "telegram" and channel_id:
            kwargs["telegram_id"] = channel_id
            if telegram_username:
                kwargs["telegram_username"] = telegram_username
        elif channel == "email" and channel_id:
            kwargs["email"] = channel_id
        elif channel == "vk" and channel_id:
            kwargs["vk_id"] = channel_id

        contact = await self.create(**kwargs)
        return contact

    async def get_by_telegram_id(
        self, telegram_id: str, include_deleted: bool = True
    ) -> Optional[ContactModel]:
        query = self._scoped(select(self.model).where(self.model.telegram_id == telegram_id))
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(
        self, email: str, include_deleted: bool = True
    ) -> Optional[ContactModel]:
        query = self._scoped(select(self.model).where(self.model.email == email))
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_vk_id(
        self, vk_id: str, include_deleted: bool = True
    ) -> Optional[ContactModel]:
        query = self._scoped(select(self.model).where(self.model.vk_id == vk_id))
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_contact_types(
        self, contact_id: int, template_ids: List[int]
    ) -> None:
        await self.session.execute(
            contact_contact_type_association.delete().where(
                contact_contact_type_association.c.contact_id == contact_id,
                contact_contact_type_association.c.owner_id == self.owner_id,
            )
        )
        for tid in template_ids:
            await self.session.execute(
                contact_contact_type_association.insert().values(
                    contact_id=contact_id,
                    template_id=tid,
                    owner_id=self.owner_id,
                )
            )
        await self.session.flush()

    async def get_contact_type_slugs(self, contact_id: int) -> List[str]:
        query = select(
            ContactTypeTemplateModel.slug,
            ContactTypeTemplateModel.name,
        ).join(
            contact_contact_type_association,
            contact_contact_type_association.c.template_id
            == ContactTypeTemplateModel.id,
        ).where(
            contact_contact_type_association.c.contact_id == contact_id,
            contact_contact_type_association.c.owner_id == self.owner_id,
        )
        result = await self.session.execute(query)
        return [name for _slug, name in result.all()]
