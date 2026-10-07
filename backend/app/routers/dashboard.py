from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import ContactModel, MessageModel, TaskModel, UserModel
from ..schemas.dashboard import (
    ChannelDistribution,
    MetricsResponse,
    PulseAnimation,
    TopContact,
)

router = APIRouter()

_cache: Dict[int, Dict[str, Any]] = {}
CACHE_TTL = 5


def invalidate_metrics_cache() -> None:
    """Сброс кэша метрик — вызывается при изменении статусов сообщений,
    чтобы badge «Входящие» обновлялся сразу, а не через CACHE_TTL."""
    _cache.clear()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MetricsResponse:
    global _cache
    now = datetime.now()
    owner_id = int(current_user.id)
    cached = _cache.get(owner_id)
    if cached and cached["data"] and cached["ts"] \
            and (now - cached["ts"]) < timedelta(seconds=CACHE_TTL):
        return cached["data"]  # type: ignore[no-any-return]
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    async def _count(model: Any, *where: Any) -> int:
        query = select(func.count()).select_from(model).where(model.owner_id == owner_id)
        for w in where:
            query = query.where(w)
        result = await session.execute(query)
        return result.scalar() or 0

    c = _count
    total_messages = await c(MessageModel)
    total_tasks = await c(TaskModel)
    total_contacts = await c(ContactModel)
    unread_messages = await c(
        MessageModel,
        MessageModel.status == "unread",
        MessageModel.deleted_at.is_(None),
    )
    unread_chats = (await session.execute(
        select(func.count(func.distinct(MessageModel.contact_id)))
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.status == "unread")
        .where(MessageModel.deleted_at.is_(None))
        .where(MessageModel.direction == "incoming")
        .where(
            or_(
                ContactModel.life_sphere.is_(None),
                ContactModel.life_sphere != "spam",
            )
        )
        .where(MessageModel.owner_id == owner_id)
    )).scalar() or 0
    answered_messages = await c(
        MessageModel,
        MessageModel.direction == "outgoing",
        MessageModel.created_at >= today_start,
    )
    completed_tasks = await c(TaskModel, TaskModel.status == "completed")

    # Контакты-«каналы»: сфера life_sphere == 'channels'.
    channel_contact_ids: set[int] = set()
    cc_rows = await session.execute(
        select(ContactModel.id).where(
            ContactModel.life_sphere == "channels"
        )
    )
    channel_contact_ids = {r[0] for r in cc_rows.all()}

    new_messages_query = (
        select(func.count(MessageModel.id))
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.owner_id == owner_id)
        .where(MessageModel.status == "unread")
        .where(MessageModel.deleted_at.is_(None))
        .where(MessageModel.direction == "incoming")
        .where(
            or_(
                ContactModel.life_sphere.is_(None),
                ContactModel.life_sphere != "spam",
            )
        )
    )
    if channel_contact_ids:
        new_messages_query = new_messages_query.where(
            ~MessageModel.contact_id.in_(channel_contact_ids)
        )
    new_messages = (await session.execute(new_messages_query)).scalar() or 0

    new_tasks = (await session.execute(
        select(func.count(TaskModel.id))
        .where(TaskModel.owner_id == owner_id)
        .where(TaskModel.deleted_at.is_(None))
        .where(
            or_(
                TaskModel.status == "new",
                and_(
                    TaskModel.status != "completed",
                    TaskModel.status != "cancelled",
                    TaskModel.due_date.is_not(None),
                    TaskModel.due_date < now,
                ),
            )
        )
    )).scalar() or 0

    active_tasks = (await session.execute(
        select(func.count(TaskModel.id))
        .where(TaskModel.owner_id == owner_id)
        .where(TaskModel.deleted_at.is_(None))
        .where(TaskModel.status.notin_(["completed", "cancelled"]))
    )).scalar() or 0

    messages_today_active_query = (
        select(func.count(MessageModel.id))
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.owner_id == owner_id)
        .where(MessageModel.created_at >= today_start)
        .where(MessageModel.direction == "incoming")
        .where(MessageModel.deleted_at.is_(None))
        .where(
            or_(
                ContactModel.life_sphere.is_(None),
                ContactModel.life_sphere != "spam",
            )
        )
    )
    if channel_contact_ids:
        messages_today_active_query = messages_today_active_query.where(
            ~MessageModel.contact_id.in_(channel_contact_ids)
        )
    messages_today_active = (await session.execute(messages_today_active_query)).scalar() or 0

    total_messages_today = (await session.execute(
        select(func.count(MessageModel.id))
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.owner_id == owner_id)
        .where(MessageModel.created_at >= today_start)
        .where(MessageModel.direction == "incoming")
        .where(ContactModel.life_sphere == "personal")
    )).scalar() or 0
    total_tasks_today = await c(
        TaskModel, TaskModel.created_at >= today_start)
    new_contacts_today = await c(
        ContactModel, ContactModel.created_at >= today_start)

    messages_yesterday = (await session.execute(
        select(func.count(MessageModel.id))
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.owner_id == owner_id)
        .where(MessageModel.created_at >= yesterday_start)
        .where(MessageModel.created_at < today_start)
        .where(MessageModel.direction == "incoming")
        .where(ContactModel.life_sphere == "personal")
    )).scalar() or 0
    tasks_yesterday = await c(
        TaskModel,
        TaskModel.created_at >= yesterday_start,
        TaskModel.created_at < today_start,
    )
    contacts_yesterday = await c(
        ContactModel,
        ContactModel.created_at >= yesterday_start,
        ContactModel.created_at < today_start,
    )

    channel_rows = await session.execute(
        select(MessageModel.channel, func.count().label("cnt"))
        .where(MessageModel.owner_id == owner_id)
        .group_by(MessageModel.channel)
    )
    channel_distribution = [
        ChannelDistribution(channel=r[0], count=r[1])
        for r in channel_rows.all()
    ]

    top_rows = await session.execute(
        select(
            ContactModel.id,
            ContactModel.name,
            func.count(MessageModel.id).label("cnt"),
        )
        .join(ContactModel, MessageModel.contact_id == ContactModel.id)
        .where(MessageModel.owner_id == owner_id)
        .group_by(ContactModel.id)
        .order_by(func.count(MessageModel.id).desc())
        .limit(5)
    )
    top_contacts = [
        TopContact(contact_id=r[0], contact_name=r[1], message_count=r[2])
        for r in top_rows.all()
    ]

    result = MetricsResponse(
        total_messages_today=total_messages_today,
        total_tasks_today=total_tasks_today,
        new_contacts_today=new_contacts_today,
        total_messages=total_messages,
        total_tasks=total_tasks,
        total_contacts=total_contacts,
        messages_yesterday=messages_yesterday,
        tasks_yesterday=tasks_yesterday,
        contacts_yesterday=contacts_yesterday,
        unread_messages=unread_messages,
        unread_chats=unread_chats,
        answered_messages=answered_messages,
        completed_tasks=completed_tasks,
        new_messages=new_messages,
        new_tasks=new_tasks,
        messages_today_active=messages_today_active,
        active_tasks=active_tasks,
        channel_distribution=channel_distribution,
        top_contacts=top_contacts,
        last_activity=now.isoformat(),
        last_updated=now,
        pulse_animation=PulseAnimation(type="pulse", intensity=0.8),
    )
    _cache[owner_id] = {"data": result, "ts": now}
    return result
