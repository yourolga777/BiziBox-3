from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from ..config import DEFAULT_OWNER_ID
from ..database import Base


class ContactFolderModel(Base):
    __tablename__ = "contact_folders"
    __table_args__ = (
        Index(
            "idx_folders_owner_category_key",
            "owner_id",
            "category_key",
            "sphere",
            unique=True,
            sqlite_where=text("category_key IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    category_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sphere: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contact_folders.id"), nullable=True, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
