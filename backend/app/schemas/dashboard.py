from datetime import datetime

from pydantic import BaseModel


class PulseAnimation(BaseModel):
    type: str
    intensity: float


class ChannelDistribution(BaseModel):
    channel: str
    count: int


class TopContact(BaseModel):
    contact_id: int
    contact_name: str | None
    message_count: int


class MetricsResponse(BaseModel):
    total_messages_today: int
    total_tasks_today: int
    new_contacts_today: int
    total_messages: int
    total_tasks: int
    total_contacts: int
    messages_yesterday: int
    tasks_yesterday: int
    contacts_yesterday: int
    unread_messages: int
    unread_chats: int = 0
    answered_messages: int
    completed_tasks: int
    new_messages: int = 0
    new_tasks: int = 0
    messages_today_active: int = 0
    active_tasks: int = 0
    channel_distribution: list[ChannelDistribution] = []
    top_contacts: list[TopContact] = []
    last_activity: str
    last_updated: datetime
    pulse_animation: PulseAnimation
