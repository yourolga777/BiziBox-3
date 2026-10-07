from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config import DEFAULT_OWNER_ID
from ..database import Base


class ImportMappingModel(Base):
    __tablename__ = "import_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        default=DEFAULT_OWNER_ID,
        server_default="1",
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapping: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
