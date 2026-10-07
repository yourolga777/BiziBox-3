from typing import Optional

from pydantic import BaseModel


class StartupChannelResult(BaseModel):
    type: str
    name: str
    connected: bool
    new_messages: int = 0
    error: Optional[str] = None


class StartupLoadResult(BaseModel):
    channels: list[StartupChannelResult]
    total_new: int = 0
