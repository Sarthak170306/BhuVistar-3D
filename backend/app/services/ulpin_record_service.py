import uuid
from typing import Optional, Union

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

