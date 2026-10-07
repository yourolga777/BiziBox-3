from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..services.backup_service import BackupError, BackupService

router = APIRouter()


@router.post("/export")
async def export_backup(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> Response:
    service = BackupService(session, owner_id=int(current_user.id))
    token = await service.export_backup()
    filename = f"bizibox-backup-{datetime.now().strftime('%Y%m%d')}.enc"
    return Response(
        content=token,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_backup(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    content = await file.read()
    service = BackupService(session, owner_id=int(current_user.id))
    try:
        result = await service.import_backup(content.decode("utf-8"))
    except (BackupError, UnicodeDecodeError):
        await session.rollback()
        raise HTTPException(
            status_code=400, detail="Повреждённый или неверный архив бэкапа"
        )
    return result
