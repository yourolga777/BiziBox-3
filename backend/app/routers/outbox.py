from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..deps import get_current_user, get_poll_service
from ..models import UserModel
from ..schemas.outbox import OutboxResponse
from ..services.outbox_service import OutboxService

router = APIRouter()


@router.get("/", response_model=List[OutboxResponse])
async def list_outbox(
    status: Optional[str] = Query(None, pattern=r"^(pending|sent|failed)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> List[OutboxResponse]:
    service = OutboxService(session, owner_id=int(current_user.id))
    items = await service.repo.list_by_status(status, skip, limit)
    return [OutboxResponse.model_validate(i) for i in items]


@router.post("/{outbox_id}/retry", response_model=OutboxResponse)
async def retry_outbox(
    outbox_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> OutboxResponse:
    service = OutboxService(session, owner_id=int(current_user.id))
    ps = get_poll_service()
    adapters = ps.channels if ps else {}
    record = await service.retry(
        outbox_id,
        adapters,
        settings.OUTBOX_MAX_ATTEMPTS,
        settings.OUTBOX_BASE_DELAY,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Outbox record not found")
    return OutboxResponse.model_validate(record)
