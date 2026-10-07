from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SupplierModel
from ..repositories.contact import ContactRepository
from ..repositories.supplier import SupplierRepository
from ..schemas.product import ProductResponse
from ..schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate


class SupplierService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.supplier_repo = SupplierRepository(session, owner_id)
        self.contact_repo = ContactRepository(session, owner_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[SupplierResponse]:
        suppliers = await self.supplier_repo.get_all(skip=skip, limit=limit)
        return [await self._to_response(s) for s in suppliers]

    async def get_by_id(self, supplier_id: int) -> Optional[SupplierResponse]:
        supplier = await self.supplier_repo.get_by_id(supplier_id)
        if not supplier:
            return None
        return await self._to_response(supplier)

    async def create(self, data: SupplierCreate) -> Optional[SupplierResponse]:
        existing = await self.supplier_repo.get_by_contact(data.contact_id)
        if existing:
            return None
        contact = await self.contact_repo.get_by_id(data.contact_id)
        if not contact:
            return None
        supplier = await self.supplier_repo.create(**data.model_dump(exclude_unset=True))
        return await self._to_response(supplier)

    async def update(self, supplier_id: int, data: SupplierUpdate) -> Optional[SupplierResponse]:
        supplier = await self.supplier_repo.update(
            supplier_id, **data.model_dump(exclude_unset=True)
        )
        if not supplier:
            return None
        return await self._to_response(supplier)

    async def delete(self, supplier_id: int) -> bool:
        return await self.supplier_repo.soft_delete(supplier_id)

    async def get_products(
        self, supplier_id: int, skip: int = 0, limit: int = 100
    ) -> List[ProductResponse]:
        products = await self.supplier_repo.get_products(supplier_id, skip=skip, limit=limit)
        responses: List[ProductResponse] = []
        for p in products:
            price = p.price if p.price is not None else 0.0
            purchase = p.purchase_price if p.purchase_price is not None else 0.0
            margin = price - purchase
            margin_percent = (margin / purchase * 100.0) if purchase else None
            responses.append(ProductResponse(
                id=p.id, owner_id=p.owner_id, name=p.name, sku=p.sku,
                price=p.price, purchase_price=p.purchase_price, stock=p.stock,
                unit=p.unit, description=p.description, supplier_id=p.supplier_id,
                deleted_at=p.deleted_at, created_at=p.created_at, updated_at=p.updated_at,
                margin=margin, margin_percent=margin_percent,
            ))
        return responses

    async def _to_response(self, supplier: SupplierModel) -> SupplierResponse:
        resp = SupplierResponse(
            id=supplier.id,
            owner_id=supplier.owner_id,
            contact_id=supplier.contact_id,
            company_name=supplier.company_name,
            inn=supplier.inn,
            notes=supplier.notes,
            deleted_at=supplier.deleted_at,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
        )
        contact = await self.contact_repo.get_by_id(int(supplier.contact_id))
        if contact:
            resp.contact_name = str(contact.name)
            resp.contact_phone = contact.phone
        return resp
