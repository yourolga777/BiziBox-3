import logging
from typing import Any

from fastapi import APIRouter

from ...deps import get_poll_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/telegram/debug")
async def debug_telegram() -> dict[str, Any]:
    ps = get_poll_service()
    result = {
        "poll_service_exists": ps is not None,
    }

    if not ps:
        return result

    adapter = ps.get_channel("telegram")
    result["adapter_exists"] = adapter is not None
    result["poll_task_running"] = (
        "telegram" in ps.tasks
        and not ps.tasks["telegram"].done()
    )
    poll_val = ps.last_poll.get("telegram")
    result["last_poll"] = str(poll_val) if poll_val else None  # type: ignore[assignment]

    if not adapter:
        return result

    client = getattr(adapter, "client", None)
    result["client_connected"] = client is not None and client.is_connected if client else False

    if not client or not client.is_connected:
        return result

    try:
        dialogs = []
        async for dialog in client.get_dialogs(limit=5):
            dialogs.append({
                "id": dialog.chat.id,
                "title": (
                    dialog.chat.title
                    or f"{dialog.chat.first_name or ''} {dialog.chat.last_name or ''}".strip()
                    or str(dialog.chat.id)
                ),
                "type": str(dialog.chat.type),
                "unread": dialog.unread_messages_count,
            })
            if len(dialogs) >= 3:
                break
        result["dialogs"] = dialogs  # type: ignore[assignment]

        if dialogs:
            messages = []
            async for msg in client.get_chat_history(dialogs[0]["id"], limit=5):
                messages.append({
                    "id": msg.id,
                    "text": (msg.text or "")[:200],
                    "outgoing": msg.outgoing,
                    "date": str(msg.date),
                    "from_id": str(msg.from_user.id) if msg.from_user else None,
                })
            result["recent_messages"] = messages  # type: ignore[assignment]
    except Exception as e:
        result["debug_error"] = str(e)  # type: ignore[assignment]

    return result
