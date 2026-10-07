from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    sku: Optional[str] = None
    price: Optional[float] = None
    purchase_price: Optional[float] = None
    stock: Optional[float] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    margin: Optional[float] = None
    margin_percent: Optional[float] = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = None
    purchase_price: Optional[float] = None
    stock: Optional[float] = None
    unit: Optional[str] = "шт"
    description: Optional[str] = None
    supplier_id: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = None
    purchase_price: Optional[float] = None
    stock: Optional[float] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    supplier_id: Optional[int] = None


class ProductSuggestItem(BaseModel):
    id: int
    name: str
    price: Optional[float] = None
    stock: Optional[float] = None
    sku: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
