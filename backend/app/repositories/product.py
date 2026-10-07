from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import ProductModel
from ..utils.search import like_predicate, search_variants
from .base import BaseRepository


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(ProductModel, session, owner_id)

    async def get_all(  # type: ignore[override]
        self,
        search: Optional[str] = None,
        supplier_id: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 100,
    ) -> List[ProductModel]:
        query = self._scoped(
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.name.asc())
        )
        if supplier_id is not None:
            query = query.where(self.model.supplier_id == supplier_id)
        if search:
            predicates = []
            for variant in search_variants(search):
                predicates.append(like_predicate(self.model.name, variant))
                predicates.append(like_predicate(self.model.sku, variant))
            query = query.where(or_(*predicates))

        if sort_by:
            col = getattr(self.model, sort_by, None)
            if col is not None:
                query = query.order_by(col.desc() if sort_order == "desc" else col.asc())

        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_deleted(self, skip: int = 0, limit: int = 100) -> List[ProductModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.deleted_at.is_not(None))
                .order_by(self.model.deleted_at.desc())
                .offset(skip).limit(limit)
            )
        )
        return list(result.scalars().all())

    async def get_by_sku(self, sku: str) -> Optional[ProductModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(self.model.sku == sku, self.model.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[ProductModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(self.model.name == name, self.model.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def next_sku_number(self, day: str) -> int:
        """Следующий порядковый номер артикула для дня `SKU-YYYY-MM-DD-`."""
        prefix = f"SKU-{day}-"
        result = await self.session.execute(
            self._scoped(
                select(self.model.sku).where(self.model.sku.like(f"{prefix}%"))
            )
        )
        max_n = 0
        for (sku,) in result.all():
            if sku:
                suffix = sku[len(prefix):]
                if suffix.isdigit():
                    max_n = max(max_n, int(suffix))
        return max_n + 1
