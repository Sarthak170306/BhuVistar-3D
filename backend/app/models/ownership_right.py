import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.owner import Owner
    from app.models.unit import Unit


class OwnershipRight(Base):
    """
    Deed, tenure right, or legal interest associated with a volumetric property unit.
    Supports fractional ownership (tenants in common, joint tenancy), leaseholds, and mortgages.
    """

    __tablename__ = "ownership_rights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="Foreign key linking to volumetric unit",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("owners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="Foreign key linking to owner",
    )
    right_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of property tenure: Freehold, Leasehold, Tenancy, Mortgage, Easement",
    )
    ownership_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        nullable=False,
        comment="Percentage share of ownership interest (0.01 to 100.00)",
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Commencement timestamp of the property tenure / title deed",
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiration timestamp for leasehold or temporary tenure rights",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="ownership_rights",
    )
    owner: Mapped["Owner"] = relationship(
        "Owner",
        back_populates="ownership_rights",
    )
