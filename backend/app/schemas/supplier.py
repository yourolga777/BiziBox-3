from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SupplierResponse(BaseModel):
    id: int
    owner_id: int
    contact_id: int
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    inn: Optional[str] = None
    notes: Optional[str] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    contact_id: int
    company_name: Optional[str] = Field(None, max_length=255)
    inn: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=255)
    inn: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
