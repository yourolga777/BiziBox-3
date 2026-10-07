from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OutboxResponse(BaseModel):
    id: int
    message_id: Optional[int] = None
    channel: str
    channel_id: str
    reply_to: Optional[str] = None
    subject: Optional[str] = None
    content: str
    status: str
    attempts: int
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
