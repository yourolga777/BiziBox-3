from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BulkIdsRequest(BaseModel):
    ids: List[int]


class OrderItemCreate(BaseModel):
    product_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=255)
    quantity: float = Field(default=1.0, ge=0)
    price: float = Field(default=0.0, ge=0)


class OrderItemUpdate(BaseModel):
    quantity: Optional[float] = Field(default=None, ge=0)
    price: Optional[float] = Field(default=None, ge=0)


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    name: str
    quantity: float
    price: float
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrderCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class OrderCommentResponse(BaseModel):
    id: int
    order_id: int
    content: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    message_id: Optional[int] = None
    delivery_address: Optional[str] = None
    payment_method: Optional[str] = None
    delivery_date: Optional[date] = None
    items: List[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    delivery_address: Optional[str] = None
    payment_method: Optional[str] = None
    delivery_date: Optional[date] = None
    paid: Optional[bool] = None


class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class OrderImportResult(BaseModel):
    created: int = 0
    skipped: int = 0
    errors: List[str] = []


class OrderResponse(BaseModel):
    id: int
    order_number: Optional[str] = None
    contact_id: int
    contact_name: Optional[str] = None
    message_id: Optional[int] = None
    status: str = "new"
    total: float = 0.0
    delivery_address: Optional[str] = None
    payment_method: Optional[str] = None
    delivery_date: Optional[date] = None
    paid: bool = False
    items: List[OrderItemResponse] = []
    comments: List[OrderCommentResponse] = []
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
