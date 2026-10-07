from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact_folder import ContactFolderModel
    from .contact_identifier import ContactIdentifierModel
    from .contact_note import ContactNoteModel
    from .contact_sphere import ContactSphereModel
    from .contact_type_template import ContactTypeTemplateModel
    from .message import MessageModel
    from .order import OrderModel
    from .supplier import SupplierModel
    from .task import TaskModel


contact_folder_association = Table(
    "contact_folder_association",
    Base.metadata,
    Column(
        "contact_id",
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "folder_id",
        Integer,
        ForeignKey("contact_folders.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("owner_id", Integer, ForeignKey("users.id"), nullable=False, server_default="1"),
)


class ContactModel(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        Index(
            "uq_contacts_owner_telegram",
            "owner_id",
            "telegram_id",
            unique=True,
            sqlite_where=text("telegram_id IS NOT NULL"),
        ),
        Index(
            "uq_contacts_owner_vk",
            "owner_id",
            "vk_id",
            unique=True,
            sqlite_where=text("vk_id IS NOT NULL"),
        ),
        Index("ix_contacts_owner_created", "owner_id", "created_at"),
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
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vk_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contact_folders.id"), nullable=True, index=True
    )
    is_known: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=True)
    life_sphere: Mapped[Optional[str]] = mapped_column(
        String(20), index=True, nullable=True
    )
    previous_life_sphere: Mapped[Optional[str]] = mapped_column(
        String(20), index=True, nullable=True
    )
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="contact")
    tasks: Mapped[List["TaskModel"]] = relationship(
        "TaskModel",
        back_populates="contact",
        foreign_keys="TaskModel.contact_id",
    )
    orders: Mapped[List["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="contact",
        foreign_keys="OrderModel.contact_id",
    )
    note_entries: Mapped[List["ContactNoteModel"]] = relationship(
        "ContactNoteModel", back_populates="contact", cascade="all, delete-orphan"
    )
    identifiers: Mapped[List["ContactIdentifierModel"]] = relationship(
        "ContactIdentifierModel", back_populates="contact", cascade="all, delete-orphan"
    )
    folder: Mapped["ContactFolderModel"] = relationship("ContactFolderModel", backref="contacts")
    folders: Mapped[List["ContactFolderModel"]] = relationship(
        "ContactFolderModel",
        secondary="contact_folder_association",
        backref="contacts_multi",
    )
    spheres: Mapped[List["ContactSphereModel"]] = relationship(
        "ContactSphereModel", back_populates="contact", cascade="all, delete-orphan"
    )
    supplier: Mapped[Optional["SupplierModel"]] = relationship(
        "SupplierModel", back_populates="contact", uselist=False
    )
    contact_types: Mapped[List["ContactTypeTemplateModel"]] = relationship(
        "ContactTypeTemplateModel",
        secondary="contact_contact_type_association",
        back_populates="contacts",
    )
