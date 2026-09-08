import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ownership_right import OwnershipRight


class Owner(Base):
    """
    Legal owner / right-holder entity (individual, corporate entity, or public authority).
    """

    __tablename__ = "owners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Authoritative identifier / citizen registry reference / masked tax ID",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Legal name of owner or institutional entity",
    )
    contact_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact detail reference or secure address record",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ownership_rights: Mapped[list["OwnershipRight"]] = relationship(
        "OwnershipRight",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
