from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .importers.entity_importers import (
    import_contacts,
    import_messages,
    import_tasks,
)


class ImportService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self._maps: Dict[str, Dict[int, int]] = {}

    async def import_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "contacts": {"created": 0, "updated": 0},
            "messages": {"created": 0, "updated": 0},
            "tasks": {"created": 0, "updated": 0},
        }

        owner_id = self.owner_id
        result["contacts"] = await import_contacts(self.session, data.get("contacts", []), self._maps, owner_id)
        result["messages"] = await import_messages(self.session, data.get("messages", []), self._maps, owner_id)
        result["tasks"] = await import_tasks(self.session, data.get("tasks", []), self._maps, owner_id)

        return result
