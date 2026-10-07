from datetime import date, datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field

ContactSphere = Literal["personal", "work", "channels", "spam"]


class ContactCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    telegram_id: Optional[str] = Field(None, max_length=100)
    telegram_username: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    life_sphere: Optional[ContactSphere] = None
    contact_type_ids: Optional[List[int]] = None
    birthday: Optional[date] = None
    is_known: Optional[bool] = None
    is_favorite: Optional[bool] = None
    folder_id: Optional[int] = None
    folder_ids: Optional[List[int]] = None


class ContactUpdate(BaseModel):
    name: Annotated[Optional[str], Field(max_length=255)] = None
    phone: Annotated[Optional[str], Field(max_length=50)] = None
    email: Annotated[Optional[str], Field(max_length=255)] = None
    telegram_id: Annotated[Optional[str], Field(max_length=100)] = None
    telegram_username: Annotated[Optional[str], Field(max_length=100)] = None
    is_known: Optional[bool] = None
    is_favorite: Optional[bool] = None
    is_blocked: Optional[bool] = None
    life_sphere: Optional[ContactSphere] = None
    contact_type_ids: Optional[List[int]] = None
    birthday: Optional[date] = None
    folder_id: Optional[int] = None
    folder_ids: Optional[List[int]] = None
    notes: Optional[str] = None


class ContactIdentifierResponse(BaseModel):
    channel: str
    value: str

    model_config = {"from_attributes": True}


class ContactFolderRef(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    sphere: Optional[str] = None
    parent_id: Optional[int] = None

    model_config = {"from_attributes": True}


class ContactResponse(BaseModel):
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None
    is_known: bool = False
    is_favorite: bool = False
    is_blocked: bool = False
    life_sphere: Optional[str] = None
    contact_types: List[str] = []
    contact_type_ids: List[int] = []
    birthday: Optional[date] = None
    notes: Optional[str] = None
    channel_types: List[str] = []
    folder_id: Optional[int] = None
    message_count: int = 0
    task_count: int = 0
    last_message_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    identifiers: List[ContactIdentifierResponse] = []
    spheres: List[str] = []
    folders: List[ContactFolderRef] = []

    model_config = {"from_attributes": True}


class MergeContactsRequest(BaseModel):
    primary_id: int
    secondary_id: int


class BulkMergeRequest(BaseModel):
    primary_id: int
    secondary_ids: List[int]


class BulkIdsRequest(BaseModel):
    ids: List[int]


class BulkUpdateRequest(BaseModel):
    ids: List[int]
    is_known: Optional[bool] = None
    folder_id: Optional[int] = None
    is_favorite: Optional[bool] = None
    life_sphere: Optional[ContactSphere] = None
    contact_type_ids: Optional[List[int]] = None


class DuplicateGroup(BaseModel):
    contacts: List[ContactResponse]
    reason: str


class TimelineEvent(BaseModel):
    type: str
    title: str
    subtitle: str
    created_at: Optional[datetime] = None
    link: Optional[str] = None


class NoteCreate(BaseModel):
    content: str = Field(min_length=1)
    author: Optional[str] = None


class NoteResponse(BaseModel):
    id: int
    content: str
    author: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactTypeTemplateCreate(BaseModel):
    sphere: ContactSphere
    name: str = Field(min_length=1, max_length=100)


class ContactTypeTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class ContactTypeTemplateResponse(BaseModel):
    id: int
    sphere: str
    name: str
    slug: Optional[str] = None
    sort_order: int = 0
    is_custom: bool = False
    is_system: bool = False

    model_config = {"from_attributes": True}
