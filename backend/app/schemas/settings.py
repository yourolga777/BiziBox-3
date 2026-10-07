from typing import Any, Dict

from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    values: Dict[str, Any]
