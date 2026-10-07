from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ContactModel, OrderCommentModel, OrderItemModel, OrderModel
from ..utils.search import like_predicate, search_variants
from .base import BaseRepository


class OrderCommentRepository(BaseRepository[OrderCommentModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(OrderCommentModel, session, owner_id)

    async def get_by_order(self, order_id: int) -> List[OrderCommentModel]:
        result = await self.session.execute(
            self._scoped(
                select(OrderCommentModel)
                .where(OrderCommentModel.order_id == order_id)
                .order_by(OrderCommentModel.created_at)
            )
        )
        return list(result.scalars().all())


class OrderItemRepository(BaseRepository[OrderItemModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(OrderItemModel, session, owner_id)

    async def get_by_order(self, order_id: int) -> List[OrderItemModel]:
        result = await self.session.execute(
            self._scoped(
                select(OrderItemModel)
                .where(OrderItemModel.order_id == order_id)
                .order_by(OrderItemModel.id)
            )
        )
        return list(result.scalars().all())


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(OrderModel, session, owner_id)

    async def get_all(  # type: ignore[override]
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        contact_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OrderModel]:
        query = self._scoped(
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        if status:
            query = query.where(self.model.status == status)
        if contact_id is not None:
            query = query.where(self.model.contact_id == contact_id)
        if search:
            query = query.join(ContactModel, ContactModel.id == self.model.contact_id)
            order_predicates = []
            for variant in search_variants(search):
                order_predicates.append(like_predicate(self.model.order_number, variant))
                order_predicates.append(like_predicate(ContactModel.name, variant))
            query = query.where(or_(*order_predicates))
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_deleted(self, skip: int = 0, limit: int = 100) -> List[OrderModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.deleted_at.is_not(None))
                .order_by(self.model.deleted_at.desc())
                .offset(skip).limit(limit)
            )
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> List[OrderModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(
                    self.model.status == status,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def next_order_sequence(self, day_prefix: str) -> int:
        result = await self.session.execute(
            self._scoped(
                select(func.count()).select_from(self.model).where(
                    self.model.order_number.like(f"{day_prefix}-%")
                )
            )
        )
        return int(result.scalar_one() or 0) + 1

    async def number_exists(self, order_number: str) -> bool:
        result = await self.session.execute(
            self._scoped(
                select(self.model.id)
                .where(self.model.order_number == order_number)
                .limit(1)
            )
        )
        return result.scalar_one_or_none() is not None
