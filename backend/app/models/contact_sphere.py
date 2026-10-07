from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config import DEFAULT_OWNER_ID
from ..database import Base

if TYPE_CHECKING:
    from .contact import ContactModel


class ContactSphereModel(Base):
    """Явные сферы контакта (множественные).

    Сферы контакта складываются из: этих явных записей + сфер его папок +
    сфер его меток (типов контакта). Спам — эксклюзивный флаг, не сфера.
    """

    __tablename__ = "contact_spheres"
    __table_args__ = (
        Index(
            "uq_cs_owner_contact_sphere",
            "owner_id",
            "contact_id",
            "sphere",
            unique=True,
        ),
        Index("ix_cs_contact_id", "contact_id", unique=False),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        default=DEFAULT_OWNER_ID,
        server_default="1",
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=False
    )
    sphere: Mapped[str] = mapped_column(String(20), nullable=False)

    contact: Mapped["ContactModel"] = relationship(
        "ContactModel", back_populates="spheres"
    )
