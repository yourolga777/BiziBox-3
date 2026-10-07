from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

EventRecurrence = Literal["daily", "weekly", "monthly"]


class CalendarEvent(BaseModel):
    """Сводное событие календаря (задача или отдельное событие)."""

    id: int
    type: str = "task"
    title: str
    date: date
    time: Optional[str] = None
    status: str
    contact_name: Optional[str] = None
    is_overdue: bool = False
    metadata: Dict[str, Any] = {}


class CalendarEventsResponse(BaseModel):
    events: List[CalendarEvent]


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    date: date
    time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    description: Optional[str] = None
    reminder_minutes: Optional[int] = Field(None, ge=0)
    recurrence: Optional[EventRecurrence] = None
    contact_id: Optional[int] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    date: Optional[date] = None
    time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    description: Optional[str] = None
    reminder_minutes: Optional[int] = Field(None, ge=0)
    recurrence: Optional[EventRecurrence] = None
    contact_id: Optional[int] = None


class CalendarEventResponse(BaseModel):
    id: int
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    title: str
    date: date
    time: Optional[str] = None
    description: Optional[str] = None
    reminder_minutes: Optional[int] = None
    recurrence: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
