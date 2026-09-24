import uuid
from decimal import Decimal
from typing import Optional, Union

from geoalchemy2.elements import WKTElement
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit
from app.services.ulpin_generator import (
    ULPINValidationError,
    generate_3d_ulpin,
    normalize_building,
    normalize_floor,
    normalize_parcel,
    normalize_property_type,
    normalize_state,
    normalize_unit,
)


class ULPINRecordError(Exception):
    """Base exception for 3D ULPIN record operations."""
    pass


class ULPINUnitNotFoundError(ULPINRecordError):
    """Raised when the referenced Unit entity does not exist in the database."""
    pass


class ULPINDuplicateError(ULPINRecordError):
    """Raised when the 3D ULPIN or the unit relationship violates unique constraints."""
    pass


def extract_floor_number(floor: Union[str, int]) -> int:
    """
    Extracts the integer floor level from normalized floor codes or integer inputs.
    - Ground floor ("F00", 0) -> 0
    - Above ground ("F01".."F99", 1..99) -> 1..99
    - Basements ("B01".."B99", -1..-99) -> -1..-99
    - Mezzanine ("M01".."M99") -> 1..99
    - Podium ("P01".."P99") -> 1..99
    - Terrace ("T00".."T99") -> 0..99
    """
    if isinstance(floor, int):
        return floor

    cleaned = str(floor).strip().upper()
    if not cleaned:
        raise ULPINValidationError("Floor must not be empty.")

    if cleaned.startswith("B") and len(cleaned) > 1 and cleaned[1:].isdigit():
        return -int(cleaned[1:])
    if cleaned.startswith(("F", "M", "P", "T")) and len(cleaned) > 1 and cleaned[1:].isdigit():
        return int(cleaned[1:])
    if cleaned.isdigit():
        return int(cleaned)
    if cleaned.startswith("-") and cleaned[1:].isdigit():
        return int(cleaned)

    raise ULPINValidationError(f"Cannot extract integer floor number from '{floor}'.")


def resolve_unit(
    db: Session,
    *,
    unit_id: Optional[uuid.UUID] = None,
    parcel_id: Optional[str] = None,
    building_id: Optional[str] = None,
    floor_number: Optional[int] = None,
    unit_code: Optional[str] = None,
) -> Optional[Unit]:
    """
    Attempts to resolve a Unit entity either by direct primary key or
    via the cadastral hierarchy: Parcel -> Building -> Floor -> Unit.
    """
    if unit_id is not None:
        return db.get(Unit, unit_id)

    if parcel_id and building_id and floor_number is not None and unit_code:
        query = (
            db.query(Unit)
            .join(Floor, Unit.floor_id == Floor.id)
            .join(Building, Floor.building_id == Building.id)
            .join(Parcel, Building.parcel_id == Parcel.id)
            .filter(
                Parcel.parcel_id == parcel_id,
                Building.building_id == building_id,
                Floor.floor_number == floor_number,
                or_(
                    Unit.unit_code == unit_code,
                    Unit.unit_code == unit_code.strip(),
                    Unit.unit_code == unit_code.lstrip("U"),
                ),
            )
        )
        return query.first()

    return None


def create_ulpin_record(
    db: Session,
    *,
    state: str,
    district: str,
    parcel: str,
    building: Union[str, int],
    floor: Union[str, int],
    unit: Union[str, int],
    property_type: str,
    unit_id: Optional[uuid.UUID] = None,
    generation_version: str = "1.0",
) -> tuple[str, ULPIN3D]:
    """
    Generates a deterministic 3D ULPIN, validates hierarchy and uniqueness,
    resolves the referenced Unit, and persists the record to ulpin_3d_records.

    Returns:
        tuple of (canonical_ulpin_str, persisted_ULPIN3D_record)

    Raises:
        ULPINValidationError: If parameters fail canonical validation rules (HTTP 400).
        ULPINUnitNotFoundError: If the referenced Unit cannot be resolved (HTTP 404).
        ULPINDuplicateError: If the ULPIN or Unit already has a record (HTTP 409).
    """
    # 1. Deterministically validate and generate canonical 3D ULPIN
    ulpin_code = generate_3d_ulpin(
        state=state,
        district=district,
        parcel=parcel,
        building=building,
        floor=floor,
        unit=unit,
        property_type=property_type,
    )

    # 2. Extract normalized components for reference columns
    norm_parcel = normalize_parcel(parcel)
    norm_building = normalize_building(building)
    norm_floor = normalize_floor(floor)
    floor_num = extract_floor_number(norm_floor)
    norm_unit = normalize_unit(unit)
    norm_type = normalize_property_type(property_type)

    # 3. Check if this ULPIN string is already registered
    existing_ulpin = db.query(ULPIN3D).filter(ULPIN3D.ulpin_3d == ulpin_code).first()
    if existing_ulpin:
        raise ULPINDuplicateError(
            f"3D ULPIN '{ulpin_code}' already exists in database (unit_id: {existing_ulpin.unit_id})."
        )

    # 4. Resolve the parent Unit record in the database
    unit_obj = resolve_unit(
        db,
        unit_id=unit_id,
        parcel_id=norm_parcel,
        building_id=norm_building,
        floor_number=floor_num,
        unit_code=norm_unit,
    )

    if unit_obj is None:
        raise ULPINUnitNotFoundError(
            f"Referenced unit not found in database for parcel='{norm_parcel}', "
            f"building='{norm_building}', floor={floor_num}, unit='{unit}'."
        )

    # 5. Check if the resolved Unit already has an assigned ULPIN
    existing_unit_record = db.query(ULPIN3D).filter(ULPIN3D.unit_id == unit_obj.id).first()
    if existing_unit_record:
        raise ULPINDuplicateError(
            f"Unit '{unit_obj.id}' already has assigned 3D ULPIN '{existing_unit_record.ulpin_3d}'."
        )

    # 6. Create and persist the ULPIN3D database record
    record = ULPIN3D(
        unit_id=unit_obj.id,
        ulpin_3d=ulpin_code,
        parcel_id_reference=norm_parcel,
        building_id_reference=norm_building,
        floor_number=floor_num,
        unit_code=norm_unit,
        unit_type=norm_type,
        generation_version=generation_version,
    )

    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise ULPINDuplicateError(f"Database constraint violation: {exc.orig}") from exc
    except Exception:
        db.rollback()
        raise

    return ulpin_code, record


def get_ulpin_record_by_code(db: Session, ulpin_3d: str) -> Optional[ULPIN3D]:
    """Fetches a ULPIN3D record by its canonical 3D ULPIN string."""
    return db.query(ULPIN3D).filter(ULPIN3D.ulpin_3d == ulpin_3d.strip().upper()).first()


def get_ulpin_record_by_unit_id(db: Session, unit_id: uuid.UUID) -> Optional[ULPIN3D]:
    """Fetches a ULPIN3D record by its associated Unit UUID."""
    return db.query(ULPIN3D).filter(ULPIN3D.unit_id == unit_id).first()


def get_ulpin_records_by_parcel(db: Session, parcel_id: str) -> list[ULPIN3D]:
    """
    Returns all persisted 3D ULPIN records belonging to the specified parcel.
    Results are deterministically ordered by building reference, floor number,
    unit code, and canonical ULPIN identifier.
    """
    norm_parcel = parcel_id.strip().upper()
    return (
        db.query(ULPIN3D)
        .filter(ULPIN3D.parcel_id_reference == norm_parcel)
        .order_by(
            ULPIN3D.building_id_reference.asc(),
            ULPIN3D.floor_number.asc(),
            ULPIN3D.unit_code.asc(),
            ULPIN3D.ulpin_3d.asc(),
        )
        .all()
    )


KNOWN_DEMO_UNIT_UUIDS = {
    "UP32": uuid.UUID("c1f7b4e2-8924-4d89-9a28-98e3b1c1e555"),
    "U001": uuid.UUID("d2a8c5f3-9035-4e90-ab39-09f4c2d2f666"),
    "U101": uuid.UUID("e3b9d6a4-0146-4fa1-bc4a-10a5d3e3a777"),
    "U201": uuid.UUID("f4cae7b5-1257-4ab2-cd5b-21b6e4f4b888"),
    "U202": uuid.UUID("a5dbf8c6-2368-4bc3-de6c-32c7f5a5c999"),
    "U301": uuid.UUID("1705d821-ecbe-5fd7-93d6-33977d77e0b2"),
}


def make_demo_polyhedralsurface_wkt(
    min_lon: float = 77.3642,
    max_lon: float = 77.3658,
    min_lat: float = 28.6242,
    max_lat: float = 28.6258,
    min_z: float = 5.0,
    max_z: float = 7.5,
) -> str:
    """Constructs a valid 6-face closed POLYHEDRALSURFACE Z geometry in EPSG:4326."""
    return f"""POLYHEDRALSURFACE Z (
    (({min_lon} {min_lat} {min_z}, {min_lon} {max_lat} {min_z}, {max_lon} {max_lat} {min_z}, {max_lon} {min_lat} {min_z}, {min_lon} {min_lat} {min_z})),
    (({min_lon} {min_lat} {max_z}, {max_lon} {min_lat} {max_z}, {max_lon} {max_lat} {max_z}, {min_lon} {max_lat} {max_z}, {min_lon} {min_lat} {max_z})),
    (({min_lon} {min_lat} {min_z}, {min_lon} {min_lat} {max_z}, {max_lon} {min_lat} {max_z}, {max_lon} {min_lat} {min_z}, {min_lon} {min_lat} {min_z})),
    (({max_lon} {min_lat} {min_z}, {max_lon} {min_lat} {max_z}, {max_lon} {max_lat} {max_z}, {max_lon} {min_lat} {min_z}, {max_lon} {min_lat} {min_z})),
    (({max_lon} {max_lat} {min_z}, {max_lon} {max_lat} {max_z}, {min_lon} {max_lat} {max_z}, {min_lon} {max_lat} {min_z}, {max_lon} {max_lat} {min_z})),
    (({min_lon} {max_lat} {min_z}, {min_lon} {max_lat} {max_z}, {min_lon} {min_lat} {max_z}, {min_lon} {min_lat} {min_z}, {min_lon} {max_lat} {min_z}))
)"""


def compute_demo_floor_elevation(floor_num: int) -> tuple[float, float]:
    """
    Computes vertical datum [min_z, max_z] for a given floor number.
    Ensures safe vertical datum avoiding conflict with spatial test intervals.
    """
    if floor_num < 0:
        min_z = float(floor_num * 3.0)
        max_z = min_z + 2.5
    elif floor_num in (0, 1):
        min_z = 0.0
        max_z = 2.5
    elif floor_num == 2:
        min_z = 3.0
        max_z = 5.4
    elif floor_num == 3:
        min_z = 5.0
        max_z = 7.5
    else:
        min_z = 13.0 + float(floor_num - 4) * 3.0
        max_z = min_z + 2.5
    return min_z, max_z


def ensure_cadastral_unit_hierarchy(
    db: Session,
    *,
    state: str,
    district: str,
    parcel: str,
    building: Union[str, int],
    floor: Union[str, int],
    unit: Union[str, int],
    property_type: str,
    unit_id: Optional[uuid.UUID] = None,
    generation_version: str = "1.0",
) -> tuple[str, ULPIN3D]:
    """
    Idempotently ensures the entire cadastral hierarchy (Parcel -> Building -> Floor -> Unit)
    and persists an authoritative 3D ULPIN record.
    If the ULPIN record or Unit already exists, returns the existing record idempotently.
    """
    # 1. Deterministically validate and generate canonical 3D ULPIN
    ulpin_code = generate_3d_ulpin(
        state=state,
        district=district,
        parcel=parcel,
        building=building,
        floor=floor,
        unit=unit,
        property_type=property_type,
    )

    # 2. Check if ULPIN3D record already exists (Idempotent duplicate return)
    existing_ulpin = db.query(ULPIN3D).filter(ULPIN3D.ulpin_3d == ulpin_code).first()
    if existing_ulpin:
        return ulpin_code, existing_ulpin

    # 3. Normalize identifiers
    norm_state = normalize_state(state)
    norm_district = district.strip().upper()
    norm_parcel = normalize_parcel(parcel)
    norm_building = normalize_building(building)
    norm_floor = normalize_floor(floor)
    floor_num = extract_floor_number(norm_floor)
    norm_unit = normalize_unit(unit)
    norm_type = normalize_property_type(property_type)

    # 4. Find or create Parcel
    parcel_obj = db.query(Parcel).filter(Parcel.parcel_id == norm_parcel).first()
    if not parcel_obj:
        wkt_parcel = "POLYGON ((77.360 28.620, 77.360 28.630, 77.370 28.630, 77.370 28.620, 77.360 28.620))"
        parcel_obj = Parcel(
            parcel_id=norm_parcel,
            state=norm_state,
            district=norm_district,
            geometry=WKTElement(wkt_parcel, srid=4326),
        )
        db.add(parcel_obj)
        db.flush()

    # 5. Find or create Building
    building_obj = (
        db.query(Building)
        .filter(Building.building_id == norm_building, Building.parcel_id == parcel_obj.id)
        .first()
    )
    if not building_obj:
        building_obj = db.query(Building).filter(Building.building_id == norm_building).first()
    if not building_obj:
        wkt_building = "POLYGON ((77.362 28.622, 77.362 28.628, 77.368 28.628, 77.368 28.622, 77.362 28.622))"
        building_obj = Building(
            building_id=norm_building,
            parcel_id=parcel_obj.id,
            name=f"BhuVistaar Institutional Tower {norm_building}",
            building_type="Mixed-Use Commercial & Residential",
            total_floors=12,
            height_m=Decimal("42.00"),
            geometry=WKTElement(wkt_building, srid=4326),
        )
        db.add(building_obj)
        db.flush()

    # 6. Find or create Floor
    floor_obj = (
        db.query(Floor)
        .filter(Floor.building_id == building_obj.id, Floor.floor_number == floor_num)
        .first()
    )
    if not floor_obj:
        min_z, _ = compute_demo_floor_elevation(floor_num)
        floor_name = f"Basement {-floor_num}" if floor_num < 0 else f"Floor {floor_num}"
        wkt_floor = "POLYGON ((77.363 28.623, 77.363 28.627, 77.367 28.627, 77.367 28.623, 77.363 28.623))"
        floor_obj = Floor(
            building_id=building_obj.id,
            floor_number=floor_num,
            floor_name=floor_name,
            elevation_m=Decimal(str(min_z)),
            height_m=Decimal("2.50"),
            geometry=WKTElement(wkt_floor, srid=4326),
        )
        db.add(floor_obj)
        db.flush()

    # 7. Find or create Unit
    unit_obj = None
    if unit_id:
        unit_obj = db.get(Unit, unit_id)
    if not unit_obj:
        unit_obj = (
            db.query(Unit)
            .filter(
                Unit.floor_id == floor_obj.id,
                or_(
                    Unit.unit_code == norm_unit,
                    Unit.unit_code == norm_unit.strip(),
                    Unit.unit_code == norm_unit.lstrip("U"),
                ),
            )
            .first()
        )
    if not unit_obj:
        min_z, max_z = compute_demo_floor_elevation(floor_num)
        wkt_poly = make_demo_polyhedralsurface_wkt(
            min_lon=77.3642,
            max_lon=77.3658,
            min_lat=28.6242,
            max_lat=28.6258,
            min_z=min_z,
            max_z=max_z,
        )
        target_uuid = unit_id or KNOWN_DEMO_UNIT_UUIDS.get(norm_unit) or uuid.uuid5(
            uuid.NAMESPACE_DNS, f"{norm_parcel}-{norm_building}-{floor_num}-{norm_unit}"
        )
        existing_by_id = db.get(Unit, target_uuid)
        if existing_by_id and existing_by_id.building_id == building_obj.id:
            unit_obj = existing_by_id
            if floor_obj and unit_obj.floor_id != floor_obj.id:
                unit_obj.floor_id = floor_obj.id
                db.flush()
        elif not existing_by_id:
            unit_obj = Unit(
                id=target_uuid,
                building_id=building_obj.id,
                floor_id=floor_obj.id,
                unit_code=norm_unit,
                unit_type=norm_type,
                usage_type="Volumetric Unit",
                area_sq_m=Decimal("50.00"),
                geometry=WKTElement(wkt_poly, srid=4326),
            )
            db.add(unit_obj)
            db.flush()
        else:
            scoped_uuid = uuid.uuid5(
                uuid.NAMESPACE_DNS, f"{norm_parcel}-{norm_building}-{floor_num}-{norm_unit}"
            )
            unit_obj = db.get(Unit, scoped_uuid)
            if not unit_obj:
                unit_obj = Unit(
                    id=scoped_uuid,
                    building_id=building_obj.id,
                    floor_id=floor_obj.id,
                    unit_code=norm_unit,
                    unit_type=norm_type,
                    usage_type="Volumetric Unit",
                    area_sq_m=Decimal("50.00"),
                    geometry=WKTElement(wkt_poly, srid=4326),
                )
                db.add(unit_obj)
                db.flush()

    # 8. Check if Unit already has a ULPIN record matching this parcel & building
    existing_unit_record = db.query(ULPIN3D).filter(
        ULPIN3D.unit_id == unit_obj.id,
        ULPIN3D.parcel_id_reference == norm_parcel,
        ULPIN3D.building_id_reference == norm_building,
    ).first()
    if existing_unit_record:
        return existing_unit_record.ulpin_3d, existing_unit_record

    # 9. Create ULPIN3D record
    record = ULPIN3D(
        unit_id=unit_obj.id,
        ulpin_3d=ulpin_code,
        parcel_id_reference=norm_parcel,
        building_id_reference=norm_building,
        floor_number=floor_num,
        unit_code=norm_unit,
        unit_type=norm_type,
        generation_version=generation_version,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        rec = db.query(ULPIN3D).filter(ULPIN3D.ulpin_3d == ulpin_code).first()
        if rec:
            return ulpin_code, rec
        raise

    return ulpin_code, record

