import json
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

TASK_STATUS_PATTERN = r"^(new|in_progress|completed|cancelled)$"

TaskRecurrence = Literal["daily", "weekly", "monthly"]


def _parse_repeat_dates(v: object) -> object:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return v


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class TaskCommentResponse(BaseModel):
    id: int
    task_id: int
    content: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskDetailResponse(BaseModel):
    id: int
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    message_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    reminder_minutes: Optional[int] = None
    reminder_at: Optional[datetime] = None
    recurrence: Optional[str] = None
    repeat_dates: Optional[List[str]] = None
    repeat_until: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    comments: List[TaskCommentResponse] = []

    model_config = {"from_attributes": True}

    @field_validator("repeat_dates", mode="before")
    @classmethod
    def _parse_rd(cls, v: object) -> object:
        return _parse_repeat_dates(v)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    contact_id: Optional[int] = None
    message_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: str = Field(default="new", pattern=TASK_STATUS_PATTERN)
    reminder_minutes: Optional[int] = Field(None, ge=0)
    recurrence: Optional[TaskRecurrence] = None
    repeat_dates: Optional[List[str]] = None
    repeat_until: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    contact_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern=TASK_STATUS_PATTERN)
    reminder_minutes: Optional[int] = Field(None, ge=0)
    recurrence: Optional[TaskRecurrence] = None
    repeat_dates: Optional[List[str]] = None
    repeat_until: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: int
    contact_id: Optional[int] = None
    message_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    reminder_minutes: Optional[int] = None
    reminder_at: Optional[datetime] = None
    recurrence: Optional[str] = None
    repeat_dates: Optional[List[str]] = None
    repeat_until: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("repeat_dates", mode="before")
    @classmethod
    def _parse_rd(cls, v: object) -> object:
        return _parse_repeat_dates(v)
