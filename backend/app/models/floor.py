import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.building import Building
    from app.models.unit import Unit


class Floor(Base):
    """
    Vertical floor level within a building structure.
    Represents vertical zoning, elevation datum, and floor plan boundary.
    """

    __tablename__ = "floors"
    __table_args__ = (
        UniqueConstraint("building_id", "floor_number", name="uq_building_floor_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="Foreign key linking to parent building",
    )
    floor_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential floor level number (negative for basements, 0 for ground, 1..N for upper floors)",
    )
    floor_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Descriptive floor label e.g., Basement 1, Ground Floor, Mezzanine, 5th Floor",
    )
    elevation_m: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Base vertical elevation above mean sea level or ground datum in meters",
    )
    height_m: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Floor-to-ceiling clear height in meters",
    )
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="POLYGON",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
        comment="2D spatial boundary / floor plate polygon in EPSG:4326",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    building: Mapped["Building"] = relationship(
        "Building",
        back_populates="floors",
    )
    units: Mapped[list["Unit"]] = relationship(
        "Unit",
        back_populates="floor",
        cascade="all, delete-orphan",
    )
