import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Date, DateTime, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Base
from ..utils.crypto import decrypt, encrypt
from ..version import VERSION

BACKUP_TABLES = frozenset(
    {
        "contacts",
        "contact_folders",
        "contact_identifiers",
        "contact_notes",
        "messages",
        "message_attachments",
        "tasks",
        "task_comments",
        "calendar_events",
        "settings",
    }
)


class BackupError(Exception):
    """Повреждённый или невалидный архив бэкапа."""


class BackupService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id

    def _tables(self) -> List[Any]:
        return [t for t in Base.metadata.sorted_tables if t.name in BACKUP_TABLES]

    async def export_backup(self) -> str:
        """Сериализует данные пользователя и шифрует их Fernet-ключом."""
        tables: Dict[str, List[Dict[str, Any]]] = {}
        for table in self._tables():
            query = select(table)
            if self.owner_id is not None and "owner_id" in table.c:
                query = query.where(table.c.owner_id == self.owner_id)
            result = await self.session.execute(query)
            tables[table.name] = [dict(row._mapping) for row in result]

        payload = {
            "meta": {
                "app": "BiziBox",
                "format": "bizibox-backup",
                "format_version": 1,
                "exported_at": datetime.now().isoformat(),
                "version": VERSION,
            },
            "tables": tables,
        }
        return encrypt(json.dumps(payload, ensure_ascii=False, default=str))

    async def import_backup(self, token: str) -> Dict[str, Any]:
        """Расшифровывает и восстанавливает данные из архива бэкапа."""
        try:
            plain = decrypt(token)
        except Exception as exc:
            raise BackupError("Не удалось расшифровать архив") from exc

        try:
            data = json.loads(plain)
        except json.JSONDecodeError as exc:
            raise BackupError("Неверный формат архива") from exc

        if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
            raise BackupError("Неверная структура архива")

        tables = self._tables()
        restored: Dict[str, int] = {}

        for table in reversed(tables):
            await self._wipe(table)

        for table in tables:
            rows = data["tables"].get(table.name, [])
            if not isinstance(rows, list):
                raise BackupError("Неверная структура архива")
            restored[table.name] = await self._insert(table, rows)

        return {"status": "success", "restored": restored}

    async def _wipe(self, table: Any) -> None:
        stmt = delete(table)
        if self.owner_id is not None and "owner_id" in table.c:
            stmt = stmt.where(table.c.owner_id == self.owner_id)
        await self.session.execute(stmt)

    async def _insert(self, table: Any, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            await self.session.execute(table.insert().values(**self._coerce(table, row)))
        return len(rows)

    def _coerce(self, table: Any, row: Dict[str, Any]) -> Dict[str, Any]:
        """Приводит ISO-строки обратно к date/datetime по типу колонки."""
        out: Dict[str, Any] = {}
        for name, value in row.items():
            column = table.c.get(name)
            if value is not None and column is not None:
                if isinstance(column.type, DateTime) and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif isinstance(column.type, Date) and isinstance(value, str):
                    value = date.fromisoformat(value)
            out[name] = value
        return out
