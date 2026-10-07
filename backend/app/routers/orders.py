import csv
import io
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..database import get_session
from ..deps import get_current_user
from ..models import OrderModel, UserModel
from ..repositories.contact import ContactRepository
from ..repositories.message import MessageRepository
from ..schemas.order import (
    BulkIdsRequest,
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
from ..services.order_extractor import OrderExtractor
from ..services.order_service import OrderService

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    contact_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[OrderResponse]:
    service = OrderService(session, owner_id=int(current_user.id))
    return await service.get_all(
        search=search, status=status, contact_id=contact_id, skip=skip, limit=limit
    )


@router.get("/archive", response_model=List[OrderResponse])
async def get_archived_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[OrderResponse]:
    service = OrderService(session, owner_id=int(current_user.id))
    return await service.get_deleted(skip=skip, limit=limit)


@router.get("/export/csv")
async def export_orders_csv(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> Response:
    stmt = (
        select(OrderModel)
        .options(
            joinedload(OrderModel.contact),
            joinedload(OrderModel.items),
        )
        .where(
            OrderModel.deleted_at.is_(None),
            OrderModel.owner_id == int(current_user.id),
        )
        .order_by(OrderModel.created_at.desc())
    )
    result = await session.execute(stmt)
    orders = result.unique().scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["№", "Клиент", "Товары", "Сумма", "Статус", "Дата"])

    status_labels = {
        "new": "Новый",
        "in_progress": "В работе",
        "shipped": "Отправлен",
        "completed": "Завершён",
        "cancelled": "Отменён",
    }

    for order in orders:
        items_str = ", ".join(
            f"{item.name} x{item.quantity}"
            for item in order.items
        )
        writer.writerow([
            order.order_number or "",
            order.contact.name if order.contact else "",
            items_str,
            order.total,
            status_labels.get(str(order.status), str(order.status)),
            order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
        ])

    content = "\uFEFF" + output.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@router.post("/import/csv", response_model=OrderImportResult)
async def import_orders_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderImportResult:
    service = OrderService(session, owner_id=int(current_user.id))
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8-sig")
    return await service.import_csv(content)


@router.post("/suggest/{message_id}")
async def suggest_order(
    message_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    message_repo = MessageRepository(session, owner_id=int(current_user.id))
    message = await message_repo.get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    extractor = OrderExtractor()
    extracted = extractor.extract(str(message.content))

    contact_repo = ContactRepository(session, owner_id=int(current_user.id))
    contact = await contact_repo.get_by_id(message.contact_id)

    return {
        "contact_id": message.contact_id,
        "contact_name": contact.name if contact else None,
        "suggested_amount": extracted["amount"] if extracted else None,
        "message_preview": str(message.content)[:200] if message.content else "",
        "confidence": extracted["confidence"] if extracted else 0.0,
    }


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.create(data)
    if not order:
        raise HTTPException(status_code=400, detail="Failed to create order")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    data: OrderUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.update(order_id, data)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = OrderService(session, owner_id=int(current_user.id))
    deleted = await service.delete(order_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Order not found")


@router.post("/{order_id}/restore", response_model=OrderResponse)
async def restore_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.restore(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/bulk-delete")
async def bulk_delete_orders(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = OrderService(session, owner_id=int(current_user.id))
    count = await service.bulk_delete(data.ids)
    return {"deleted": count}


@router.post("/bulk-restore")
async def bulk_restore_orders(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = OrderService(session, owner_id=int(current_user.id))
    count = await service.bulk_restore(data.ids)
    return {"restored": count}


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    try:
        order = await service.update_status(order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/{order_id}/comments", response_model=List[OrderCommentResponse])
async def get_order_comments(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[OrderCommentResponse]:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.comments


@router.post("/{order_id}/comments", response_model=OrderCommentResponse, status_code=201)
async def create_order_comment(
    order_id: int,
    data: OrderCommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderCommentResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    comment = await service.add_comment(order_id, data)
    if not comment:
        raise HTTPException(status_code=404, detail="Order not found")
    return comment


@router.delete("/{order_id}/comments/{comment_id}", status_code=204)
async def delete_order_comment(
    order_id: int,
    comment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = OrderService(session, owner_id=int(current_user.id))
    order = await service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    deleted = await service.delete_comment(comment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")


@router.post("/{order_id}/items", response_model=OrderItemResponse, status_code=201)
async def add_order_item(
    order_id: int,
    data: OrderItemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderItemResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    item = await service.add_item(order_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Order not found")
    return item


@router.delete("/{order_id}/items/{item_id}", status_code=204)
async def remove_order_item(
    order_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = OrderService(session, owner_id=int(current_user.id))
    deleted = await service.remove_item(order_id, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")


@router.patch("/{order_id}/items/{item_id}", response_model=OrderItemResponse)
async def update_order_item(
    order_id: int,
    item_id: int,
    data: OrderItemUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OrderItemResponse:
    service = OrderService(session, owner_id=int(current_user.id))
    item = await service.update_item(order_id, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
