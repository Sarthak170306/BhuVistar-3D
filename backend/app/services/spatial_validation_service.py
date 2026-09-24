import uuid
from typing import Any, Optional, Union

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.unit import Unit


class SpatialValidationError(ValueError):
    """Base exception for spatial hierarchy and geometry validation errors."""
    pass


class InvalidGeometryError(SpatialValidationError):
    """Raised when a geometry is invalid according to PostGIS ST_IsValid, empty, malformed, or has an unexpected SRID."""
    pass


class SpatialContainmentError(SpatialValidationError):
    """Raised when a child geometry is not spatially contained within its parent geometry boundary."""
    pass


def check_geometry_validity_and_srid(
    db: Session,
    geom: Any,
    entity_name: str = "Geometry",
    expected_srid: int = 4326,
    allow_none: bool = False,
    raise_on_error: bool = True,
) -> tuple[bool, str]:
    """
    Evaluates geometry validity using PostGIS ST_IsValid, ST_IsValidReason, ST_SRID, and ST_IsEmpty.
    Does not silently repair geometry.
    """
    if geom is None:
        if allow_none:
            return True, f"{entity_name} geometry is omitted (optional)."
        msg = f"{entity_name} geometry is missing or null."
        if raise_on_error:
            raise InvalidGeometryError(msg)
        return False, msg

    try:
        gtype = db.execute(select(func.ST_GeometryType(geom))).scalar()
        if gtype == "ST_PolyhedralSurface":
            stmt = select(
                func.ST_SRID(geom),
                func.ST_IsEmpty(geom),
                func.ST_NumGeometries(geom),
            )
            srid, is_empty, num_faces = db.execute(stmt).one()
            is_valid = bool(num_faces is not None and num_faces >= 4)
            reason = "Valid PolyhedralSurface" if is_valid else "PolyhedralSurface has fewer than 4 faces"
        else:
            stmt = select(
                func.ST_IsValid(geom),
                func.ST_IsValidReason(geom),
                func.ST_SRID(geom),
                func.ST_IsEmpty(geom),
            )
            is_valid, reason, srid, is_empty = db.execute(stmt).one()
    except Exception as exc:
        msg = f"{entity_name} geometry is malformed or could not be processed by PostGIS: {exc}."
        if raise_on_error:
            raise InvalidGeometryError(msg) from exc
        return False, msg

    if is_empty:
        msg = f"{entity_name} geometry is empty."
        if raise_on_error:
            raise InvalidGeometryError(msg)
        return False, msg

    if not is_valid:
        msg = f"{entity_name} geometry is invalid: {reason}."
        if raise_on_error:
            raise InvalidGeometryError(msg)
        return False, msg

    if srid != expected_srid:
        msg = f"{entity_name} geometry has invalid SRID {srid}, expected {expected_srid}."
        if raise_on_error:
            raise InvalidGeometryError(msg)
        return False, msg

    return True, f"{entity_name} geometry is valid."


def check_spatial_containment(
    db: Session,
    child_geom: Any,
    parent_geom: Any,
    child_name: str = "Child",
    parent_name: str = "Parent",
    raise_on_error: bool = True,
) -> tuple[bool, str]:
    """
    Evaluates whether child_geom is spatially contained within parent_geom.
    Uses PostGIS ST_Covers and ST_Within with ST_Force2D for 2D/3D polygons,
    or ST_Envelope for 3D polyhedral surfaces.
    """
    if child_geom is None or parent_geom is None:
        msg = f"Cannot evaluate spatial containment: {child_name} or {parent_name} geometry is missing."
        if raise_on_error:
            raise SpatialContainmentError(msg)
        return False, msg

    try:
        gtype = db.execute(select(func.ST_GeometryType(child_geom))).scalar()
        if gtype == "ST_PolyhedralSurface":
            target_child = func.ST_Envelope(child_geom)
        else:
            target_child = func.ST_Force2D(child_geom)

        stmt = select(
            or_(
                func.ST_Covers(parent_geom, target_child),
                func.ST_Within(target_child, parent_geom),
            )
        )
        is_contained = bool(db.execute(stmt).scalar())
    except Exception as exc:
        msg = f"Failed to evaluate spatial containment between {child_name} and {parent_name}: {exc}."
        if raise_on_error:
            raise SpatialContainmentError(msg) from exc
        return False, msg

    if not is_contained:
        msg = f"{child_name} is not spatially contained within {parent_name} boundary."
        if raise_on_error:
            raise SpatialContainmentError(msg)
        return False, msg

    return True, f"{child_name} is spatially contained within {parent_name}."


def validate_parcel_geometry(
    db: Session,
    parcel: Parcel,
    expected_srid: int = 4326,
    raise_on_error: bool = True,
) -> bool:
    """
    Validates a cadastral land parcel boundary polygon.
    """
    valid, _ = check_geometry_validity_and_srid(
        db,
        parcel.geometry,
        entity_name="Parcel",
        expected_srid=expected_srid,
        allow_none=False,
        raise_on_error=raise_on_error,
    )
    return valid


def validate_building_geometry(
    db: Session,
    building: Building,
    expected_srid: int = 4326,
    raise_on_error: bool = True,
) -> bool:
    """
    Validates a building footprint polygon.
    """
    valid, _ = check_geometry_validity_and_srid(
        db,
        building.geometry,
        entity_name="Building",
        expected_srid=expected_srid,
        allow_none=False,
        raise_on_error=raise_on_error,
    )
    return valid


def validate_floor_geometry(
    db: Session,
    floor: Floor,
    expected_srid: int = 4326,
    allow_none: bool = True,
    raise_on_error: bool = True,
) -> bool:
    """
    Validates a floor spatial boundary polygon.
    Floor geometry can be optional (allow_none=True) when vertical zoning relies on elevation datums.
    """
    valid, _ = check_geometry_validity_and_srid(
        db,
        floor.geometry,
        entity_name="Floor",
        expected_srid=expected_srid,
        allow_none=allow_none,
        raise_on_error=raise_on_error,
    )
    return valid


def validate_unit_geometry(
    db: Session,
    unit: Unit,
    expected_srid: int = 4326,
    allow_none: bool = False,
    raise_on_error: bool = True,
) -> bool:
    """
    Validates a 3D volumetric property unit geometry (GEOMETRYZ in EPSG:4326).
    """
    valid, _ = check_geometry_validity_and_srid(
        db,
        unit.geometry,
        entity_name="Unit",
        expected_srid=expected_srid,
        allow_none=allow_none,
        raise_on_error=raise_on_error,
    )
    return valid


def validate_building_within_parcel(
    db: Session,
    building: Building,
    parcel: Optional[Parcel] = None,
    raise_on_error: bool = True,
) -> bool:
    """
    Verifies that building footprint geometry is spatially contained within its parent parcel.
    """
    if parcel is None:
        parcel = building.parcel or db.query(Parcel).filter(Parcel.id == building.parcel_id).first()
    if parcel is None:
        msg = f"Building '{building.building_id}' has no associated parent parcel."
        if raise_on_error:
            raise SpatialValidationError(msg)
        return False

    contained, _ = check_spatial_containment(
        db,
        child_geom=building.geometry,
        parent_geom=parcel.geometry,
        child_name="Building footprint",
        parent_name="parent parcel",
        raise_on_error=raise_on_error,
    )
    return contained


def validate_unit_within_parent(
    db: Session,
    unit: Unit,
    floor: Optional[Floor] = None,
    building: Optional[Building] = None,
    raise_on_error: bool = True,
) -> bool:
    """
    Verifies that unit geometry is spatially contained within its parent floor or building geometry.
    """
    if floor is None and unit.floor_id is not None:
        floor = unit.floor or db.query(Floor).filter(Floor.id == unit.floor_id).first()
    if building is None and unit.building_id is not None:
        building = unit.building or db.query(Building).filter(Building.id == unit.building_id).first()

    parent_geom = None
    parent_name = "parent"

    if floor is not None and floor.geometry is not None:
        parent_geom = floor.geometry
        parent_name = "parent floor"
    elif building is not None and building.geometry is not None:
        parent_geom = building.geometry
        parent_name = "parent building"
    else:
        msg = f"Unit '{unit.unit_code}' has no parent geometry defined (neither floor nor building geometry available)."
        if raise_on_error:
            raise SpatialValidationError(msg)
        return False

    contained, _ = check_spatial_containment(
        db,
        child_geom=unit.geometry,
        parent_geom=parent_geom,
        child_name=f"Unit '{unit.unit_code}'",
        parent_name=parent_name,
        raise_on_error=raise_on_error,
    )
    return contained


def validate_unit_spatial_hierarchy(
    db: Session,
    unit_id: Union[uuid.UUID, str],
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """
    Performs comprehensive spatial hierarchy validation for Parcel -> Building -> Floor -> Unit.

    Verifies:
    1. Building footprint is spatially contained within parent parcel boundary.
    2. Floor geometry is spatially contained within parent building footprint when both are available.
    3. Unit geometry is spatially contained within parent floor/building geometry.
    4. Geometries are valid according to PostGIS ST_IsValid.
    5. Geometries have expected SRID 4326.
    6. Empty/null geometries are safely handled without unhandled errors.
    7. Read-only operation: does not modify any geometry.

    Returns structured dictionary with:
    - success: bool
    - valid: bool
    - unit_id: str
    - checks: dict with unit_geometry_valid, floor_geometry_valid, building_geometry_valid,
              building_within_parcel, unit_within_parent
    - errors: list[str]
    """
    # 1. Parse / resolve UUID
    if isinstance(unit_id, str):
        try:
            parsed_id = uuid.UUID(unit_id)
        except (ValueError, AttributeError) as exc:
            if raise_on_error:
                raise SpatialValidationError(f"Invalid unit UUID: '{unit_id}'") from exc
            return {
                "success": False,
                "valid": False,
                "unit_id": str(unit_id),
                "checks": {
                    "unit_geometry_valid": False,
                    "floor_geometry_valid": False,
                    "building_geometry_valid": False,
                    "building_within_parcel": False,
                    "unit_within_parent": False,
                },
                "errors": [f"Invalid unit UUID: '{unit_id}'"],
            }
    else:
        parsed_id = unit_id

    # 2. Fetch Unit entity
    unit = db.query(Unit).filter(Unit.id == parsed_id).first()
    if not unit:
        from app.services.ulpin_record_service import ULPINUnitNotFoundError
        raise ULPINUnitNotFoundError(f"Unit '{parsed_id}' not found in database.")

    # 3. Resolve parent entities through hierarchy: Unit -> Floor -> Building -> Parcel
    floor = unit.floor or (db.query(Floor).filter(Floor.id == unit.floor_id).first() if unit.floor_id else None)
    building = unit.building or (db.query(Building).filter(Building.id == unit.building_id).first() if unit.building_id else None)
    if building is None and floor is not None:
        building = floor.building or (db.query(Building).filter(Building.id == floor.building_id).first() if floor.building_id else None)
    parcel = (building.parcel or (db.query(Parcel).filter(Parcel.id == building.parcel_id).first() if building and building.parcel_id else None)) if building else None

    errors: list[str] = []

    # Check 1: unit_geometry_valid
    unit_valid, unit_msg = check_geometry_validity_and_srid(
        db,
        unit.geometry,
        entity_name="Unit",
        expected_srid=4326,
        allow_none=False,
        raise_on_error=False,
    )
    if not unit_valid:
        errors.append(unit_msg)

    # Check 2: floor_geometry_valid
    # Safely handle optional floor geometry: if None, valid is True.
    # If present, must be valid ST_IsValid and ST_SRID, AND contained in building footprint when both available.
    if floor is None or floor.geometry is None:
        floor_valid = True
    else:
        floor_valid, floor_msg = check_geometry_validity_and_srid(
            db,
            floor.geometry,
            entity_name="Floor",
            expected_srid=4326,
            allow_none=True,
            raise_on_error=False,
        )
        if not floor_valid:
            errors.append(floor_msg)
        elif building is not None and building.geometry is not None:
            # Check floor containment inside building
            floor_contained, floor_cont_msg = check_spatial_containment(
                db,
                child_geom=floor.geometry,
                parent_geom=building.geometry,
                child_name="Floor plate",
                parent_name="parent building",
                raise_on_error=False,
            )
            if not floor_contained:
                floor_valid = False
                errors.append(floor_cont_msg)

    # Check 3: building_geometry_valid
    if building is None:
        bldg_valid = False
        errors.append("Unit is not linked to a parent building.")
    else:
        bldg_valid, bldg_msg = check_geometry_validity_and_srid(
            db,
            building.geometry,
            entity_name="Building",
            expected_srid=4326,
            allow_none=False,
            raise_on_error=False,
        )
        if not bldg_valid:
            errors.append(bldg_msg)

    # Check 4: building_within_parcel
    if not bldg_valid or building is None:
        bldg_within_parcel = False
    elif parcel is None:
        bldg_within_parcel = False
        errors.append("Building is not linked to a parent parcel.")
    else:
        parcel_valid, parcel_msg = check_geometry_validity_and_srid(
            db,
            parcel.geometry,
            entity_name="Parcel",
            expected_srid=4326,
            allow_none=False,
            raise_on_error=False,
        )
        if not parcel_valid:
            bldg_within_parcel = False
            errors.append(parcel_msg)
        else:
            bldg_contained, bldg_cont_msg = check_spatial_containment(
                db,
                child_geom=building.geometry,
                parent_geom=parcel.geometry,
                child_name="Building footprint",
                parent_name="parent parcel",
                raise_on_error=False,
            )
            bldg_within_parcel = bldg_contained
            if not bldg_contained:
                errors.append(bldg_cont_msg)

    # Check 5: unit_within_parent
    if not unit_valid:
        unit_within_parent = False
    else:
        # Unit's parent geometry is floor geometry if available, else building geometry
        parent_geom = None
        parent_label = "parent"

        if floor is not None and floor.geometry is not None and floor_valid:
            parent_geom = floor.geometry
            parent_label = "parent floor"
        elif building is not None and building.geometry is not None and bldg_valid:
            parent_geom = building.geometry
            parent_label = "parent building"

        if parent_geom is None:
            unit_within_parent = False
            errors.append("No valid parent geometry (floor or building) available to check unit containment.")
        else:
            unit_contained, unit_cont_msg = check_spatial_containment(
                db,
                child_geom=unit.geometry,
                parent_geom=parent_geom,
                child_name=f"Unit '{unit.unit_code}'",
                parent_name=parent_label,
                raise_on_error=False,
            )
            unit_within_parent = unit_contained
            if not unit_contained:
                errors.append(unit_cont_msg)

    all_valid = (
        unit_valid
        and floor_valid
        and bldg_valid
        and bldg_within_parcel
        and unit_within_parent
    )

    checks = {
        "unit_geometry_valid": unit_valid,
        "floor_geometry_valid": floor_valid,
        "building_geometry_valid": bldg_valid,
        "building_within_parcel": bldg_within_parcel,
        "unit_within_parent": unit_within_parent,
    }

    if raise_on_error and not all_valid:
        err_first = errors[0] if errors else "Spatial hierarchy validation failed."
        if not bldg_within_parcel or not unit_within_parent:
            raise SpatialContainmentError(err_first)
        elif not unit_valid or not bldg_valid or not floor_valid:
            raise InvalidGeometryError(err_first)
        else:
            raise SpatialValidationError(err_first)

    return {
        "success": True,
        "valid": all_valid,
        "unit_id": str(unit.id),
        "checks": checks,
        "errors": errors,
    }
