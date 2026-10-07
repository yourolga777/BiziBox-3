from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import ProductModel
from ..models.supplier import SupplierModel
from .base import BaseRepository


class SupplierRepository(BaseRepository[SupplierModel]):
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        super().__init__(SupplierModel, session, owner_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SupplierModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.deleted_at.is_(None))
                .order_by(self.model.company_name.asc())
                .offset(skip).limit(limit)
            )
        )
        return list(result.scalars().all())

    async def get_deleted(self, skip: int = 0, limit: int = 100) -> List[SupplierModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model)
                .where(self.model.deleted_at.is_not(None))
                .order_by(self.model.deleted_at.desc())
                .offset(skip).limit(limit)
            )
        )
        return list(result.scalars().all())

    async def get_by_contact(self, contact_id: int) -> Optional[SupplierModel]:
        result = await self.session.execute(
            self._scoped(
                select(self.model).where(self.model.contact_id == contact_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_products(self, supplier_id: int, skip: int = 0, limit: int = 100) -> List[ProductModel]:
        query = select(ProductModel).where(
            ProductModel.supplier_id == supplier_id,
            ProductModel.deleted_at.is_(None),
        )
        if self.owner_id is not None:
            query = query.where(ProductModel.owner_id == self.owner_id)
        query = query.order_by(ProductModel.name.asc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
