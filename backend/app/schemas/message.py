from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _snooze_must_be_future(v: Optional[datetime]) -> Optional[datetime]:
    if v is None:
        return v
    now = datetime.now()
    if v.tzinfo is not None:
        now = now.astimezone(v.tzinfo)
    if v <= now:
        raise ValueError("snoozed_until must be in the future")
    return v


class AttachmentInput(BaseModel):
    channel_message_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_path: Optional[str] = None


class AttachmentResponse(BaseModel):
    id: int
    message_id: int
    channel_message_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    contact_id: int
    channel: str = Field(..., max_length=50)
    channel_message_id: Optional[str] = None
    reply_to: Optional[str] = None
    subject: Optional[str] = None
    content: str = Field("", min_length=0)
    direction: str = Field(..., pattern=r"^(incoming|outgoing)$")
    status: str = Field(default="unread", pattern=r"^(unread|read|archived)$")
    snoozed_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    attachments: Optional[list[AttachmentInput]] = None

    _validate_snooze = field_validator("snoozed_until")(_snooze_must_be_future)


class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, pattern=r"^(unread|read|archived)$")
    contact_id: Optional[int] = Field(None, ge=1)
    is_flagged: Optional[bool] = None
    is_pinned: Optional[bool] = None
    snoozed_until: Optional[datetime] = None

    _validate_snooze = field_validator("snoozed_until")(_snooze_must_be_future)


class SnoozeRequest(BaseModel):
    until: datetime

    _validate_snooze = field_validator("until")(_snooze_must_be_future)


class BulkStatusUpdate(BaseModel):
    ids: list[int] = Field(..., min_length=1)
    status: str = Field(..., pattern=r"^(unread|read|archived)$")


class BulkIdsRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class BulkActionRequest(BaseModel):
    ids: list[int] = Field(...)


class MessageResponse(BaseModel):
    id: int
    contact_id: int
    contact_name: Optional[str] = None
    contact_username: Optional[str] = None
    channel: str
    channel_message_id: Optional[str] = None
    reply_to: Optional[str] = None
    subject: Optional[str] = None
    content: str
    content_html: Optional[str] = None
    direction: str
    status: str
    attachments: list[AttachmentResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_flagged: bool = False
    is_pinned: bool = False
    snoozed_until: Optional[datetime] = None
    extracted_code: Optional[str] = None

    model_config = {"from_attributes": True}


class ThreadResponse(BaseModel):
    contact_id: int
    last_message: MessageResponse
    unread_count: int = 0
    channels: list[str] = []


class LoadPreviousRequest(BaseModel):
    contact_id: int
    count: int = Field(default=10, ge=1, le=50)
