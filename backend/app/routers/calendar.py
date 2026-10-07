from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.calendar import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventsResponse,
    CalendarEventUpdate,
)
from ..services.calendar_service import CalendarService

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/events", response_model=CalendarEventsResponse)
async def get_events(
    start: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    end: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CalendarEventsResponse:
    service = CalendarService(session, owner_id=int(current_user.id))
    events = await service.get_events(start, end)
    return CalendarEventsResponse(events=events)


@router.post("/events", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    data: CalendarEventCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CalendarEventResponse:
    service = CalendarService(session, owner_id=int(current_user.id))
    return await service.create_event(data)


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CalendarEventResponse:
    service = CalendarService(session, owner_id=int(current_user.id))
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/events/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: int,
    data: CalendarEventUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CalendarEventResponse:
    service = CalendarService(session, owner_id=int(current_user.id))
    event = await service.update_event(event_id, data)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = CalendarService(session, owner_id=int(current_user.id))
    deleted = await service.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
