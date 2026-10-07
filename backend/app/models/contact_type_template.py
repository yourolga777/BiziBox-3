from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact import ContactModel

contact_contact_type_association = Table(
    "contact_contact_type_association",
    Base.metadata,
    Column(
        "contact_id",
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "template_id",
        Integer,
        ForeignKey("contact_type_templates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("owner_id", Integer, ForeignKey("users.id"), nullable=False, server_default="1"),
)


class ContactTypeTemplateModel(Base):
    __tablename__ = "contact_type_templates"
    __table_args__ = (
        Index(
            "uq_ctt_owner_slug",
            "owner_id",
            "slug",
            unique=True,
            sqlite_where=text("slug IS NOT NULL"),
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
    sphere: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    contacts: Mapped[List["ContactModel"]] = relationship(
        "ContactModel",
        secondary="contact_contact_type_association",
        back_populates="contact_types",
    )
