from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit


class SpatialValidationError(ValueError):
    """Raised when spatial query parameters (coordinates, bounding box bounds, or elevations) are invalid."""
    pass


def validate_coordinates(lon: float, lat: float, name_prefix: str = "") -> None:
    """Validates longitude (-180 to 180) and latitude (-90 to 90)."""
    prefix = f"{name_prefix} " if name_prefix else ""
    if not (-180.0 <= lon <= 180.0):
        raise SpatialValidationError(f"{prefix}Longitude must be between -180.0 and 180.0, got {lon}.")
    if not (-90.0 <= lat <= 90.0):
        raise SpatialValidationError(f"{prefix}Latitude must be between -90.0 and 90.0, got {lat}.")


def validate_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
    """Validates bounding box coordinate ranges and ordering."""
    validate_coordinates(min_lon, min_lat, name_prefix="Minimum")
    validate_coordinates(max_lon, max_lat, name_prefix="Maximum")
    if min_lon > max_lon:
        raise SpatialValidationError(
            f"Invalid bounding box: min_lon ({min_lon}) cannot be greater than max_lon ({max_lon})."
        )
    if min_lat > max_lat:
        raise SpatialValidationError(
            f"Invalid bounding box: min_lat ({min_lat}) cannot be greater than max_lat ({max_lat})."
        )


def validate_z_range(min_z: float, max_z: float) -> None:
    """Validates vertical elevation range ordering."""
    if min_z > max_z:
        raise SpatialValidationError(
            f"Invalid vertical range: min_z ({min_z}) cannot be greater than max_z ({max_z})."
        )


def find_ulpins_within_bbox(
    db: Session,
    *,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> list[ULPIN3D]:
    """
    Returns all persisted 3D ULPIN records whose spatial geometry intersects
    the requested bounding box in EPSG:4326.

    Uses PostGIS ST_MakeEnvelope and ST_Intersects on the database side.
    Evaluates unit 3D geometry, falling back to parent building or parcel ground footprint.
    """
    validate_bbox(min_lon, min_lat, max_lon, max_lat)

    envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    spatial_geom = func.coalesce(Unit.geometry, Building.geometry, Parcel.geometry)

    return (
        db.query(ULPIN3D)
        .join(Unit, ULPIN3D.unit_id == Unit.id)
        .outerjoin(Floor, Unit.floor_id == Floor.id)
        .outerjoin(Building, Unit.building_id == Building.id)
        .outerjoin(Parcel, Building.parcel_id == Parcel.id)
        .filter(
            spatial_geom.is_not(None),
            func.ST_Intersects(spatial_geom, envelope),
        )
        .order_by(
            ULPIN3D.building_id_reference.asc(),
            ULPIN3D.floor_number.asc(),
            ULPIN3D.unit_code.asc(),
            ULPIN3D.ulpin_3d.asc(),
        )
        .all()
    )


def find_ulpins_at_point(
    db: Session,
    *,
    longitude: float,
    latitude: float,
) -> list[ULPIN3D]:
    """
    Returns persisted 3D ULPIN records whose spatial geometry intersects
    the requested horizontal XY point in EPSG:4326.

    Uses PostGIS ST_SetSRID, ST_MakePoint, and ST_Intersects.
    """
    validate_coordinates(longitude, latitude)

    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    spatial_geom = func.coalesce(Unit.geometry, Building.geometry, Parcel.geometry)

    return (
        db.query(ULPIN3D)
        .join(Unit, ULPIN3D.unit_id == Unit.id)
        .outerjoin(Floor, Unit.floor_id == Floor.id)
        .outerjoin(Building, Unit.building_id == Building.id)
        .outerjoin(Parcel, Building.parcel_id == Parcel.id)
        .filter(
            spatial_geom.is_not(None),
            func.ST_Intersects(spatial_geom, point),
        )
        .order_by(
            ULPIN3D.building_id_reference.asc(),
            ULPIN3D.floor_number.asc(),
            ULPIN3D.unit_code.asc(),
            ULPIN3D.ulpin_3d.asc(),
        )
        .all()
    )


def find_ulpins_by_height_range(
    db: Session,
    *,
    min_z: float,
    max_z: float,
) -> list[ULPIN3D]:
    """
    Returns records whose vertical 3D spatial extent overlaps the requested vertical range (meters).
    Evaluates both 3D geometry coordinates (ST_ZMin / ST_ZMax) and floor elevation datums.
    """
    validate_z_range(min_z, max_z)

    geom_z_match = and_(
        Unit.geometry.is_not(None),
        func.ST_HasZ(Unit.geometry),
        func.ST_ZMin(Unit.geometry) <= max_z,
        func.ST_ZMax(Unit.geometry) >= min_z,
    )

    floor_z_match = and_(
        Floor.elevation_m.is_not(None),
        Floor.elevation_m <= max_z,
        (Floor.elevation_m + func.coalesce(Floor.height_m, 3.0)) >= min_z,
    )

    return (
        db.query(ULPIN3D)
        .join(Unit, ULPIN3D.unit_id == Unit.id)
        .outerjoin(Floor, Unit.floor_id == Floor.id)
        .filter(
            or_(
                geom_z_match,
                floor_z_match,
            )
        )
        .order_by(
            ULPIN3D.building_id_reference.asc(),
            ULPIN3D.floor_number.asc(),
            ULPIN3D.unit_code.asc(),
            ULPIN3D.ulpin_3d.asc(),
        )
        .all()
    )


def find_ulpins_intersecting_geometry(
    db: Session,
    *,
    geometry_wkt: str,
    srid: int = 4326,
) -> list[ULPIN3D]:
    """
    General PostGIS intersection query against an arbitrary WKT geometry string.
    """
    geom = func.ST_GeomFromText(geometry_wkt, srid)
    spatial_geom = func.coalesce(Unit.geometry, Building.geometry, Parcel.geometry)

    return (
        db.query(ULPIN3D)
        .join(Unit, ULPIN3D.unit_id == Unit.id)
        .outerjoin(Floor, Unit.floor_id == Floor.id)
        .outerjoin(Building, Unit.building_id == Building.id)
        .outerjoin(Parcel, Building.parcel_id == Parcel.id)
        .filter(
            spatial_geom.is_not(None),
            func.ST_Intersects(spatial_geom, geom),
        )
        .order_by(
            ULPIN3D.building_id_reference.asc(),
            ULPIN3D.floor_number.asc(),
            ULPIN3D.unit_code.asc(),
            ULPIN3D.ulpin_3d.asc(),
        )
        .all()
    )
