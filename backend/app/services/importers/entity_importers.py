from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models import (
    ContactModel,
    MessageModel,
    TaskModel,
)
from ...repositories.base import BaseRepository
from .base import clean, id_map, upsert


async def import_contacts(
    session: AsyncSession, items: list[dict[str, Any]], maps: dict[str, dict[int, int]],
    owner_id: Optional[int] = None,
) -> dict[str, int]:
    created = 0
    updated = 0
    repo: BaseRepository[Any] = BaseRepository(ContactModel, session, owner_id)
    for item in items:
        old_id = item.get("id")
        c, u = await upsert(
            session, repo, ContactModel, old_id,
            "telegram_id", item.get("telegram_id"),
            maps,
            **clean(item),
        )
        created += c
        updated += u
    return {"created": created, "updated": updated}


async def import_messages(
    session: AsyncSession, items: list[dict[str, Any]], maps: dict[str, dict[int, int]],
    owner_id: Optional[int] = None,
) -> dict[str, int]:
    created = 0
    updated = 0
    repo: BaseRepository[Any] = BaseRepository(MessageModel, session, owner_id)
    for item in items:
        old_id = item.get("id")
        item_clean = clean(item)
        contact_id = item_clean.pop("contact_id", None)
        mapped = id_map(maps, contact_id)
        if contact_id is not None and mapped is not None:
            item_clean["contact_id"] = mapped

        channel = item.get("channel")
        channel_msg_id = item.get("channel_message_id")
        unique_val = f"{channel}::{channel_msg_id}" if channel and channel_msg_id else None

        c, u = await upsert(
            session, repo, MessageModel, old_id,
            "id" if not unique_val else None, None if unique_val else None,
            maps,
            **item_clean,
        )
        created += c
        updated += u
    return {"created": created, "updated": updated}


async def import_tasks(
    session: AsyncSession, items: list[dict[str, Any]], maps: dict[str, dict[int, int]],
    owner_id: Optional[int] = None,
) -> dict[str, int]:
    created = 0
    updated = 0
    repo: BaseRepository[Any] = BaseRepository(TaskModel, session, owner_id)
    for item in items:
        old_id = item.get("id")
        item_clean = clean(item)
        contact_id = item_clean.pop("contact_id", None)
        mapped_contact = id_map(maps, contact_id)
        if contact_id is not None and mapped_contact is not None:
            item_clean["contact_id"] = mapped_contact
        item_clean.pop("message_id", None)
        c, u = await upsert(
            session, repo, TaskModel, old_id, None, None, maps, **item_clean,
        )
        created += c
        updated += u
    return {"created": created, "updated": updated}
