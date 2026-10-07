from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ReminderResponse(BaseModel):
    kind: Literal["task", "event"]
    id: int
    title: str
    fired_at: Optional[datetime] = None
    recurrence: Optional[str] = None
    when: Optional[datetime] = None
