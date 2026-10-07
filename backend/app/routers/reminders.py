from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.reminder import ReminderResponse
from ..services.reminder_scheduler import ReminderService

router = APIRouter()


@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ReminderResponse]:
    service = ReminderService(session, owner_id=int(current_user.id))
    return [ReminderResponse(**r) for r in await service.get_fired(limit=limit)]


@router.post("/{kind}/{reminder_id}/ack", response_model=dict)
async def ack_reminder(
    kind: str,
    reminder_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, bool]:
    if kind not in ("task", "event"):
        raise HTTPException(status_code=400, detail="Invalid reminder kind")
    service = ReminderService(session, owner_id=int(current_user.id))
    ok = await service.ack(kind, reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"acked": True}
