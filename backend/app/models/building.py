import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.floor import Floor
    from app.models.parcel import Parcel
    from app.models.unit import Unit


class Building(Base):
    """
    Building structure erected on a cadastral parcel.
    Stores building footprint geometry in EPSG:4326.
    """

    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique identifier for the building entity",
    )
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parcels.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="Foreign key linking to parent cadastral parcel",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name or designation of the building / tower",
    )
    building_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Classification e.g., Residential, Commercial, Mixed-use, Industrial",
    )
    total_floors: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total count of floors including basements",
    )
    height_m: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Total architectural height of the structure in meters",
    )
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="POLYGON",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
        comment="2D footprint polygon of the building on the parcel (EPSG:4326)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    parcel: Mapped["Parcel"] = relationship(
        "Parcel",
        back_populates="buildings",
    )
    floors: Mapped[list["Floor"]] = relationship(
        "Floor",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    units: Mapped[list["Unit"]] = relationship(
        "Unit",
        back_populates="building",
        cascade="all, delete-orphan",
    )
