import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..services.import_service import ImportService

router = APIRouter()

REQUIRED_KEYS = {"contacts", "messages", "tasks"}


@router.post("/all")
async def import_all(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "Поддерживаются только .json файлы")

    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "Неверный формат JSON")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise HTTPException(400, f"Отсутствуют обязательные ключи: {', '.join(sorted(missing))}")

    service = ImportService(session, owner_id=int(current_user.id))
    result = await service.import_all(data)

    return {"status": "success", "imported": result}
