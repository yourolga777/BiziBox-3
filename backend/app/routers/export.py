from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import (
    ContactModel,
    MessageModel,
    TaskModel,
    UserModel,
)
from ..version import VERSION

router = APIRouter()


def _model_to_dict(row: Any, skip: set[str] = {"_sa_instance_state"}) -> Dict[str, Any]:
    d = {}
    for col in row.__table__.columns:
        if col.name not in skip:
            val = getattr(row, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            d[col.name] = val
    return d


async def _fetch_all(session: AsyncSession, model: type[Any], owner_id: int) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(model).where(model.owner_id == owner_id)
    )
    return [_model_to_dict(row) for row in result.scalars().all()]


@router.get("/all")
async def export_all(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> Response:
    owner_id = int(current_user.id)
    contacts = await _fetch_all(session, ContactModel, owner_id)
    messages = await _fetch_all(session, MessageModel, owner_id)
    tasks = await _fetch_all(session, TaskModel, owner_id)

    data = {
        "meta": {
            "exported_at": datetime.now().isoformat(),
            "version": VERSION,
            "app": "BiziBox",
        },
        "contacts": contacts,
        "messages": messages,
        "tasks": tasks,
    }

    import json
    json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)

    return Response(
        content=json_str.encode("utf-8"),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename=bizibox-export-{datetime.now().strftime("%Y%m%d")}.json'
        },
    )
