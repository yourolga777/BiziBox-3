from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ContactFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=7)
    sort_order: int = 0
    category_key: Optional[str] = Field(None, max_length=50)
    sphere: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[int] = None


class ContactFolderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=7)
    sort_order: Optional[int] = None
    category_key: Optional[str] = Field(None, max_length=50)
    sphere: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[int] = None


class FolderReorderRequest(BaseModel):
    ids: List[int] = Field(min_length=1)


class ContactFolderResponse(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    category_key: Optional[str] = None
    sphere: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
