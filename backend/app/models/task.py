from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact import ContactModel


class TaskCommentModel(Base):
    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        default=DEFAULT_OWNER_ID,
        server_default="1",
        index=True,
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="comments")


class TaskModel(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_owner_created", "owner_id", "created_at"),
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
    contact_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    message_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminder_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repeat_dates: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repeat_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminder_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    contact: Mapped["ContactModel"] = relationship(
        "ContactModel",
        back_populates="tasks",
        foreign_keys=[contact_id],
    )
    comments: Mapped[List["TaskCommentModel"]] = relationship(
        "TaskCommentModel",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskCommentModel.created_at",
    )

    @property
    def reminder_at(self) -> Optional[datetime]:
        """Время напоминания = due_date - reminder_minutes.

        None, если due_date или reminder_minutes не заданы.
        """
        if self.due_date is None or self.reminder_minutes is None:
            return None
        return self.due_date - timedelta(minutes=self.reminder_minutes)
