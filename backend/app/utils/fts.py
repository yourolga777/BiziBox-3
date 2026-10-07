import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

FTS_TABLE = "messages_fts"

_CREATE_FTS_SQL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
    "content, owner_id UNINDEXED, message_id UNINDEXED, tokenize='unicode61')"
)


def build_fts_query(q: str) -> str:
    """Собирает FTS5 MATCH-выражение: каждый токен — префиксный запрос."""
    parts: List[str] = []
    for raw in q.split():
        token = raw.strip()
        if not token:
            continue
        parts.append(f'"{_escape(token)}"*')
    return " AND ".join(parts)


def _escape(token: str) -> str:
    return token.replace('"', '""')


async def ensure_table(session: AsyncSession) -> bool:
    try:
        await session.execute(text(_CREATE_FTS_SQL))
        return True
    except Exception as e:
        logger.warning("FTS5 unavailable, search/indexing disabled: %s", e)
        return False


async def index_message(
    session: AsyncSession, message_id: int, owner_id: int, content: str
) -> None:
    if not await ensure_table(session):
        return
    await session.execute(
        text(
            "INSERT INTO messages_fts(content, owner_id, message_id) "
            "VALUES (:content, :owner_id, :message_id)"
        ),
        {"content": content or "", "owner_id": owner_id, "message_id": message_id},
    )


async def reindex_message(
    session: AsyncSession, message_id: int, owner_id: int, content: str
) -> None:
    await deindex_message(session, message_id)
    await index_message(session, message_id, owner_id, content)


async def deindex_message(session: AsyncSession, message_id: int) -> None:
    if not await ensure_table(session):
        return
    await session.execute(
        text("DELETE FROM messages_fts WHERE message_id = :message_id"),
        {"message_id": message_id},
    )


async def search_message_ids(
    session: AsyncSession, q: str, owner_id: int, limit: int = 200
) -> List[int]:
    if not q.strip():
        return []
    if not await ensure_table(session):
        return []
    query = build_fts_query(q.strip())
    if not query:
        return []
    result = await session.execute(
        text(
            "SELECT message_id FROM messages_fts "
            "WHERE messages_fts MATCH :q AND owner_id = :owner_id "
            "ORDER BY message_id DESC LIMIT :limit"
        ),
        {"q": query, "owner_id": owner_id, "limit": limit},
    )
    return [int(row[0]) for row in result.all()]
