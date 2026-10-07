import csv
import io
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DEFAULT_OWNER_ID
from ..models import (
    ContactFolderModel,
    ContactModel,
    ContactTypeTemplateModel,
    OrderItemModel,
    ProductModel,
    SupplierModel,
    contact_contact_type_association,
    contact_folder_association,
)
from ..repositories.contact import ContactRepository
from ..repositories.product import ProductRepository
from ..repositories.supplier import SupplierRepository
from ..schemas.product import (
    ProductCreate,
    ProductImportResult,
    ProductResponse,
    ProductSuggestItem,
    ProductUpdate,
)
from ..utils.csv_utils import detect_delimiter


class ProductService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.product_repo = ProductRepository(session, owner_id)
        self.supplier_repo = SupplierRepository(session, owner_id)
        self.contact_repo = ContactRepository(session, owner_id)

    async def get_all(
        self,
        search: Optional[str] = None,
        supplier_id: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 100,
    ) -> List[ProductResponse]:
        products = await self.product_repo.get_all(
            search=search,
            supplier_id=supplier_id,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )
        return await self._enrich(products)

    async def get_deleted(self, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        products = await self.product_repo.get_deleted(skip=skip, limit=limit)
        return await self._enrich(products)

    async def get_by_id(self, product_id: int) -> Optional[ProductResponse]:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None
        enriched = await self._enrich([product])
        return enriched[0]

    async def create(self, data: ProductCreate) -> Optional[ProductResponse]:
        payload = data.model_dump(exclude_unset=True)
        if not payload.get("sku"):
            today = datetime.now().strftime("%Y-%m-%d")
            n = await self.product_repo.next_sku_number(today)
            payload["sku"] = f"SKU-{today}-{n}"
        else:
            existing = await self.product_repo.get_by_sku(payload["sku"])
            if existing:
                return None
        product = await self.product_repo.create(**payload)
        enriched = await self._enrich([product])
        return enriched[0]

    async def update(self, product_id: int, data: ProductUpdate) -> Optional[ProductResponse]:
        if data.sku:
            existing = await self.product_repo.get_by_sku(data.sku)
            if existing and int(existing.id) != product_id:
                return None
        product = await self.product_repo.update(
            product_id, **data.model_dump(exclude_unset=True)
        )
        if not product:
            return None
        enriched = await self._enrich([product])
        return enriched[0]

    async def delete(self, product_id: int) -> bool:
        return await self.product_repo.soft_delete(product_id)

    async def permanent_delete(self, product_id: int) -> bool:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return False
        await self.session.execute(
            update(OrderItemModel)
            .where(OrderItemModel.product_id == product_id)
            .values(product_id=None)
        )
        return await self.product_repo.delete(product_id)

    async def restore(self, product_id: int) -> Optional[ProductResponse]:
        product = await self.product_repo.restore(product_id)
        if not product:
            return None
        enriched = await self._enrich([product])
        return enriched[0]

    async def suggest(self, query: str, limit: int = 10) -> List[ProductSuggestItem]:
        products = await self.product_repo.get_all(search=query, limit=limit)
        return [ProductSuggestItem.model_validate(p) for p in products]

    async def export_csv(self) -> str:
        products = await self.product_repo.get_all(limit=10000)
        enriched = await self._enrich(products)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "id", "name", "sku", "price", "purchase_price", "stock",
            "unit", "description", "supplier", "created_at", "updated_at",
        ])
        for p in enriched:
            writer.writerow([
                p.id, p.name, p.sku or "", p.price or "", p.purchase_price or "",
                p.stock if p.stock is not None else "", p.unit or "",
                p.description or "", p.supplier_name or "",
                p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
                p.updated_at.strftime("%Y-%m-%d %H:%M:%S") if p.updated_at else "",
            ])
        return output.getvalue()

    async def import_csv(self, content: str) -> ProductImportResult:
        delimiter = detect_delimiter(content)
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        created = 0
        updated = 0
        skipped = 0

        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                skipped += 1
                continue

            sku = (row.get("sku") or "").strip() or None
            price = _to_float(row.get("price"))
            purchase_price = _to_float(row.get("purchase_price"))
            stock = _to_float(row.get("stock"))
            unit = (row.get("unit") or "").strip() or None
            description = (row.get("description") or "").strip() or None
            supplier_name = (row.get("supplier") or "").strip()

            supplier_id = await self._resolve_supplier(supplier_name)

            existing = None
            if sku:
                existing = await self.product_repo.get_by_sku(sku)
            if not existing:
                existing = await self.product_repo.get_by_name(name)

            if existing:
                update_data = {
                    "name": name,
                }
                if sku:
                    update_data["sku"] = sku
                if price is not None:
                    update_data["price"] = price
                if purchase_price is not None:
                    update_data["purchase_price"] = purchase_price
                if stock is not None:
                    update_data["stock"] = stock
                if unit:
                    update_data["unit"] = unit
                if description:
                    update_data["description"] = description
                if supplier_id is not None:
                    update_data["supplier_id"] = supplier_id
                await self.product_repo.update(int(existing.id), **update_data)
                updated += 1
            else:
                await self.product_repo.create(
                    name=name,
                    sku=sku,
                    price=price,
                    purchase_price=purchase_price,
                    stock=stock,
                    unit=unit,
                    description=description,
                    supplier_id=supplier_id,
                )
                created += 1

        return ProductImportResult(created=created, updated=updated, skipped=skipped)

    async def _resolve_supplier(self, supplier_name: str) -> Optional[int]:
        if not supplier_name:
            return None
        result = await self.session.execute(
            select(ContactModel).where(
                ContactModel.name == supplier_name,
                ContactModel.owner_id == self.owner_id,
                ContactModel.deleted_at.is_(None),
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            contact = await self.contact_repo.create(name=supplier_name)
        await self._apply_supplier_classification(int(contact.id))
        supplier = await self.supplier_repo.get_by_contact(int(contact.id))
        if not supplier:
            supplier = await self.supplier_repo.create(contact_id=int(contact.id))
        return int(supplier.id)

    async def _apply_supplier_classification(self, contact_id: int) -> None:
        """Кладёт контакт в папку «Поставщики» (work) и вешает метку «Поставщик»."""
        owner_id = self.owner_id or DEFAULT_OWNER_ID
        folder_row = await self.session.execute(
            select(ContactFolderModel).where(
                ContactFolderModel.category_key == "suppliers",
                ContactFolderModel.owner_id == owner_id,
            )
        )
        folder = folder_row.scalar_one_or_none()
        if folder is None:
            return
        await self.contact_repo.update(
            contact_id, life_sphere="work", folder_id=int(folder.id)
        )
        await self.session.execute(
            contact_folder_association.insert().values(
                owner_id=owner_id, contact_id=contact_id, folder_id=int(folder.id)
            )
        )
        tpl_row = await self.session.execute(
            select(ContactTypeTemplateModel.id).where(
                ContactTypeTemplateModel.slug == "supplier",
                ContactTypeTemplateModel.owner_id == owner_id,
            )
        )
        tpl_id = tpl_row.scalar_one_or_none()
        if tpl_id is not None:
            existing = await self.session.execute(
                select(contact_contact_type_association.c.template_id).where(
                    contact_contact_type_association.c.contact_id == contact_id
                )
            )
            existing_ids = [int(t) for t in existing.scalars().all()]
            if int(tpl_id) not in existing_ids:
                await self.session.execute(
                    contact_contact_type_association.insert().values(
                        contact_id=contact_id,
                        template_id=tpl_id,
                        owner_id=owner_id,
                    )
                )
        await self.session.flush()

    async def _enrich(self, products: List[ProductModel]) -> List[ProductResponse]:
        supplier_ids = {int(p.supplier_id) for p in products if p.supplier_id is not None}
        supplier_map: dict[int, str] = {}
        if supplier_ids:
            result = await self.session.execute(
                select(SupplierModel, ContactModel)
                .join(ContactModel, ContactModel.id == SupplierModel.contact_id)
                .where(SupplierModel.id.in_(supplier_ids))
            )
            for supplier, contact in result.all():
                supplier_map[int(supplier.id)] = str(contact.name) if contact.name else str(supplier.company_name or "")

        responses: List[ProductResponse] = []
        for p in products:
            price = p.price if p.price is not None else 0.0
            purchase = p.purchase_price if p.purchase_price is not None else 0.0
            margin = price - purchase
            margin_percent = (margin / purchase * 100.0) if purchase else None
            resp = ProductResponse(
                id=p.id,
                owner_id=p.owner_id,
                name=p.name,
                sku=p.sku,
                price=p.price,
                purchase_price=p.purchase_price,
                stock=p.stock,
                unit=p.unit,
                description=p.description,
                supplier_id=p.supplier_id,
                supplier_name=supplier_map.get(int(p.supplier_id)) if p.supplier_id is not None else None,
                deleted_at=p.deleted_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
                margin=margin,
                margin_percent=margin_percent,
            )
            responses.append(resp)
        return responses


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
