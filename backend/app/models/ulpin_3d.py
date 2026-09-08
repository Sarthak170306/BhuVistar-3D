import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.unit import Unit


class ULPIN3D(Base):
    """
    3D Unique Land Parcel Identification Number (3D ULPIN) entity.
    Provides volumetric cadastre identification for 3D units above/below ground.
    """

    __tablename__ = "ulpin_3d_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
        comment="Foreign key linking 1-to-1 with volumetric unit",
    )
    ulpin_3d: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Algorithmic 3D Unique Land Parcel Identification Number",
    )
    parcel_id_reference: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="Authoritative parent parcel identifier reference",
    )
    building_id_reference: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="Authoritative parent building identifier reference",
    )
    floor_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Vertical level index of the unit",
    )
    unit_code: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Unit reference code within floor/building",
    )
    unit_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit classification e.g. Flat, Commercial, Parking",
    )
    generation_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0",
        nullable=False,
        comment="ULPIN standard generation algorithm specification version",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="ulpin_3d",
    )
