from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user, get_poll_service
from ..models import UserModel
from ..schemas.startup import StartupLoadResult
from ..services.channel_service import ChannelService

router = APIRouter()


@router.post("/load", response_model=StartupLoadResult)
async def startup_load(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> StartupLoadResult:
    ps = get_poll_service()
    service = ChannelService(session, owner_id=int(current_user.id))
    result: dict[str, Any] = await service.startup_load(ps)  # type: ignore[arg-type]
    return StartupLoadResult(**result)
