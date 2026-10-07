from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact import ContactModel


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        Index("ix_calendar_events_owner_date", "owner_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        default=DEFAULT_OWNER_ID,
        server_default="1",
        index=True,
    )
    contact_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reminder_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminder_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    contact: Mapped["ContactModel"] = relationship("ContactModel")
