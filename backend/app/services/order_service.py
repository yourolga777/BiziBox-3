import csv
import io
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ContactModel, OrderModel, ProductModel
from ..repositories.contact import ContactRepository
from ..repositories.order import OrderCommentRepository, OrderItemRepository, OrderRepository
from ..repositories.product import ProductRepository
from ..schemas.order import (
    OrderCommentCreate,
    OrderCommentResponse,
    OrderCreate,
    OrderImportResult,
    OrderItemCreate,
    OrderItemResponse,
    OrderItemUpdate,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)
from ..utils.csv_utils import detect_delimiter, parse_items_text


class OrderService:
    ALLOWED_STATUSES = ["new", "in_progress", "shipped", "completed", "cancelled"]

    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.order_repo = OrderRepository(session, owner_id)
        self.item_repo = OrderItemRepository(session, owner_id)
        self.comment_repo = OrderCommentRepository(session, owner_id)
        self.contact_repo = ContactRepository(session, owner_id)
        self.product_repo = ProductRepository(session, owner_id)

    async def get_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        contact_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OrderResponse]:
        orders = await self.order_repo.get_all(
            search=search,
            status=status,
            contact_id=contact_id,
            skip=skip,
            limit=limit,
        )
        return [await self._to_response(o) for o in orders]

    async def get_deleted(
        self, skip: int = 0, limit: int = 100
    ) -> List[OrderResponse]:
        orders = await self.order_repo.get_deleted(skip=skip, limit=limit)
        return [await self._to_response(o) for o in orders]

    async def get_by_id(self, order_id: int) -> Optional[OrderResponse]:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None
        return await self._to_response(order)

    async def create(self, data: OrderCreate) -> Optional[OrderResponse]:
        total = sum(item.quantity * item.price for item in data.items)

        contact_id = data.contact_id
        if contact_id is None:
            if data.contact_name:
                new_contact = await self.contact_repo.create(
                    name=data.contact_name,
                    phone=data.contact_phone,
                    email=data.contact_email,
                )
                contact_id = int(new_contact.id)
            else:
                return None

        day = datetime.now().strftime("%Y%m%d")
        base_seq = await self.order_repo.next_order_sequence(day)

        order = None
        for offset in range(1000):
            number = f"ORD-{day}-{base_seq + offset:04d}"
            try:
                async with self.session.begin_nested():
                    order = await self.order_repo.create(
                        order_number=number,
                        contact_id=contact_id,
                        message_id=data.message_id,
                        status="new",
                        total=total,
                        delivery_address=data.delivery_address,
                        payment_method=data.payment_method,
                        delivery_date=data.delivery_date,
                        paid=False,
                    )
                    for item in data.items:
                        await self.item_repo.create(
                            order_id=order.id,
                            product_id=item.product_id,
                            name=item.name,
                            quantity=item.quantity,
                            price=item.price,
                        )
                break
            except IntegrityError:
                order = None
        if order is None:
            return None

        return await self._to_response(order)

    async def update(
        self, order_id: int, data: OrderUpdate
    ) -> Optional[OrderResponse]:
        order = await self.order_repo.update(
            order_id,
            **data.model_dump(exclude_unset=True),
        )
        if not order:
            return None
        return await self._to_response(order)

    async def delete(self, order_id: int) -> bool:
        return await self.order_repo.soft_delete(order_id)

    async def restore(self, order_id: int) -> Optional[OrderResponse]:
        order = await self.order_repo.restore(order_id)
        if not order:
            return None
        return await self._to_response(order)

    async def bulk_delete(self, ids: List[int]) -> int:
        count = 0
        for oid in ids:
            if await self.order_repo.soft_delete(oid):
                count += 1
        return count

    async def bulk_restore(self, ids: List[int]) -> int:
        count = 0
        for oid in ids:
            if await self.order_repo.restore(oid):
                count += 1
        return count

    async def update_status(
        self, order_id: int, data: OrderStatusUpdate
    ) -> Optional[OrderResponse]:
        if data.status not in self.ALLOWED_STATUSES:
            raise ValueError(
                f"Invalid status: {data.status}. "
                f"Allowed: {', '.join(self.ALLOWED_STATUSES)}"
            )
        order = await self.order_repo.update(order_id, status=data.status)
        if not order:
            return None
        return await self._to_response(order)

    async def add_item(
        self, order_id: int, item_data: OrderItemCreate
    ) -> Optional[OrderItemResponse]:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None

        item = await self.item_repo.create(
            order_id=order_id,
            product_id=item_data.product_id,
            name=item_data.name,
            quantity=item_data.quantity,
            price=item_data.price,
        )

        await self._recalculate_total(order_id)
        return OrderItemResponse.model_validate(item)

    async def remove_item(self, order_id: int, item_id: int) -> bool:
        item = await self.item_repo.get_by_id(item_id)
        if not item or item.order_id != order_id:
            return False
        deleted = await self.item_repo.delete(item_id)
        if deleted:
            await self._recalculate_total(order_id)
        return deleted

    async def update_item(
        self, order_id: int, item_id: int, item_data: OrderItemUpdate
    ) -> Optional[OrderItemResponse]:
        item = await self.item_repo.get_by_id(item_id)
        if not item or item.order_id != order_id:
            return None
        payload = item_data.model_dump(exclude_unset=True)
        if payload:
            item = await self.item_repo.update(item_id, **payload)
            await self._recalculate_total(order_id)
        return OrderItemResponse.model_validate(item)

    async def _recalculate_total(self, order_id: int) -> None:
        items = await self.item_repo.get_by_order(order_id)
        total = sum(item.quantity * item.price for item in items)
        await self.order_repo.update(order_id, total=total)

    async def add_comment(
        self, order_id: int, data: OrderCommentCreate
    ) -> Optional[OrderCommentResponse]:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None
        comment = await self.comment_repo.create(order_id=order_id, content=data.content)
        return OrderCommentResponse.model_validate(comment)

    async def delete_comment(self, comment_id: int) -> bool:
        return await self.comment_repo.delete(comment_id)

    async def import_csv(self, content: str) -> OrderImportResult:
        delimiter = detect_delimiter(content)
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        raws = list(reader)
        if not raws:
            return OrderImportResult()

        norm_map = {_norm(h): h for h in (reader.fieldnames or []) if h}

        def col(*names: str) -> Optional[str]:
            for name in names:
                if name in norm_map:
                    return norm_map[name]
            return None

        created = 0
        skipped = 0
        errors: List[str] = []

        for idx, row in enumerate(raws, start=2):
            try:
                client = ((row.get(col("клиент", "Клиент", "имя", "name") or "") or "").strip())
                if not client:
                    raise ValueError("не указан клиент")

                contact = await self._resolve_contact(client)

                items_text = ((row.get(col("товары", "Товары", "items") or "") or "").strip())
                parsed_items = parse_items_text(items_text)
                if not parsed_items:
                    raise ValueError("нет позиций")

                total = _csv_float(row.get(col("сумма", "Сумма", "total") or ""))
                status = _csv_status(row.get(col("статус", "Статус", "status") or ""))
                number = ((row.get(col("№", "номер", "order_number", "num") or "") or "").strip())
                created_at = _csv_dt(row.get(col("дата", "Дата", "date", "created_at") or ""))

                item_inputs: List[OrderItemCreate] = []
                only_one = len(parsed_items) == 1
                for name, qty in parsed_items:
                    price: Optional[float] = None
                    product = await self._find_product(name)
                    if product is not None and product.price is not None:
                        price = product.price
                    elif only_one and total:
                        price = round(total / qty, 2)
                    item_inputs.append(
                        OrderItemCreate(name=name, quantity=qty, price=price if price is not None else 0.0)
                    )

                if not number or await self.order_repo.number_exists(number):
                    day = datetime.now().strftime("%Y%m%d")
                    number = f"ORD-{day}-{await self.order_repo.next_order_sequence(day):04d}"

                saved = None
                for _attempt in range(5):
                    try:
                        async with self.session.begin_nested():
                            order = await self.order_repo.create(
                                order_number=number,
                                contact_id=int(contact.id),
                                message_id=None,
                                status=status,
                                total=total or 0.0,
                                delivery_address=None,
                                payment_method=None,
                                paid=False,
                                created_at=created_at,
                            )
                            for item_input in item_inputs:
                                await self.item_repo.create(
                                    order_id=order.id,
                                    product_id=item_input.product_id,
                                    name=item_input.name,
                                    quantity=item_input.quantity,
                                    price=item_input.price,
                                )
                        saved = order
                        break
                    except IntegrityError:
                        day = datetime.now().strftime("%Y%m%d")
                        number = f"ORD-{day}-{await self.order_repo.next_order_sequence(day):04d}"
                if saved is None:
                    raise ValueError("не удалось сохранить заказ: номер занят")
                created += 1
            except Exception as exc:
                errors.append(f"строка {idx}: {exc}")
                skipped += 1

        return OrderImportResult(created=created, skipped=skipped, errors=errors)

    async def _resolve_contact(self, name: str) -> "ContactModel":
        result = await self.session.execute(
            select(ContactModel).where(
                ContactModel.name == name,
                ContactModel.owner_id == self.owner_id,
                ContactModel.deleted_at.is_(None),
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            contact = await self.contact_repo.create(name=name)
        return contact

    async def _find_product(self, name: str) -> "Optional[ProductModel]":
        return await self.product_repo.get_by_name(name)

    async def _to_response(self, order: OrderModel) -> OrderResponse:
        resp = OrderResponse(
            id=order.id,
            order_number=order.order_number,
            contact_id=order.contact_id,
            message_id=order.message_id,
            status=order.status,
            total=order.total,
            delivery_address=order.delivery_address,
            payment_method=order.payment_method,
            delivery_date=order.delivery_date,
            paid=order.paid,
            deleted_at=order.deleted_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        contact = await self.contact_repo.get_by_id(int(order.contact_id))
        if contact:
            resp.contact_name = str(contact.name)
        items = await self.item_repo.get_by_order(int(order.id))
        resp.items = [OrderItemResponse.model_validate(i) for i in items]
        comments = await self.comment_repo.get_by_order(int(order.id))
        resp.comments = [OrderCommentResponse.model_validate(c) for c in comments]
        return resp


_STATUS_LABELS = {
    "новый": "new",
    "в работе": "in_progress",
    "отправлен": "shipped",
    "завершён": "completed",
    "завершен": "completed",
    "отменён": "cancelled",
    "отменен": "cancelled",
}


def _norm(value: str) -> str:
    return value.strip().lower()


def _csv_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(" ", "").replace("руб", "").replace("₽", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _csv_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _csv_status(value: Optional[str]) -> str:
    if not value:
        return "new"
    key = str(value).strip().lower()
    if key in OrderService.ALLOWED_STATUSES:
        return key
    return _STATUS_LABELS.get(key, "new")
