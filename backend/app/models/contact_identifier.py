from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact import ContactModel


class ContactIdentifierModel(Base):
    """Дополнительные идентификаторы контакта (несколько Telegram/email/телефон).

    Основной идентификатор хранится в самом контакте (telegram_id/email/phone);
    сюда складываются альтернативные адреса — в частности, при объединении
    дублей, чтобы не терять ни один логин/адрес вторичного контакта.
    """

    __tablename__ = "contact_identifiers"
    __table_args__ = (
        Index(
            "uq_ci_owner_contact_channel_value",
            "owner_id",
            "contact_id",
            "channel",
            "value",
            unique=True,
        ),
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
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    contact: Mapped["ContactModel"] = relationship(
        "ContactModel", back_populates="identifiers"
    )
