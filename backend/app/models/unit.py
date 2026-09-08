import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.building import Building
    from app.models.floor import Floor
    from app.models.ownership_right import OwnershipRight
    from app.models.ulpin_3d import ULPIN3D


class Unit(Base):
    """
    Volumetric property unit (flat, apartment, shop, office, parking bay).
    Geometry uses a 3D-aware representation (GEOMETRYZ with dimension=3 in EPSG:4326)
    supporting 3D polygons, extruded prisms, and future 3D polyhedral solids.
    """

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("floor_id", "unit_code", name="uq_floor_unit_code"),
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
    floor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("floors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="Foreign key linking to specific floor level",
    )
    unit_code: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Unit identifier e.g., Flat 402, Shop G-12, Parking P2-45",
    )
    unit_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Category: Apartment, Commercial Suite, Shop, Parking Bay, Utility",
    )
    area_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Carpet / volumetric floor area of the unit in square meters",
    )
    usage_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Functional usage: Residential, Retail, Office, Storage, Vehicle Parking",
    )
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="GEOMETRYZ",
            srid=4326,
            dimension=3,
            spatial_index=True,
        ),
        nullable=True,
        comment="3D volumetric spatial geometry (POLYGONZ / POLYHEDRALSURFACEZ in EPSG:4326)",
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
    building: Mapped["Building"] = relationship(
        "Building",
        back_populates="units",
    )
    floor: Mapped["Floor"] = relationship(
        "Floor",
        back_populates="units",
    )
    ownership_rights: Mapped[list["OwnershipRight"]] = relationship(
        "OwnershipRight",
        back_populates="unit",
        cascade="all, delete-orphan",
    )
    ulpin_3d: Mapped["ULPIN3D | None"] = relationship(
        "ULPIN3D",
        back_populates="unit",
        uselist=False,
        cascade="all, delete-orphan",
    )
