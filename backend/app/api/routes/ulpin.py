import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ulpin_3d import ULPIN3D
from app.schemas.ulpin import (
    ULPINErrorResponse,
    ULPINGenerateRequest,
    ULPINGenerateResponse,
    ULPINParcelCollectionResponse,
    ULPINRecordData,
    ULPINRetrieveResponse,
    ULPINSpatialCollectionResponse,
)
from app.services.ulpin_generator import (
    ULPINValidationError,
    generate_3d_ulpin,
    normalize_building,
    normalize_floor,
    normalize_parcel,
    normalize_unit,
)
from app.services.ulpin_record_service import (
    ULPINDuplicateError,
    ULPINUnitNotFoundError,
    create_ulpin_record,
    ensure_cadastral_unit_hierarchy,
    extract_floor_number,
    get_ulpin_record_by_code,
    get_ulpin_record_by_unit_id,
    get_ulpin_records_by_parcel,
    resolve_unit,
)
from app.services.ulpin_spatial_service import (
    SpatialValidationError,
    find_ulpins_at_point,
    find_ulpins_by_height_range,
    find_ulpins_within_bbox,
)

router = APIRouter()


@router.post(
    "/generate",
    response_model=ULPINGenerateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINGenerateResponse,
            "description": "3D ULPIN generated without database persistence",
        },
        status.HTTP_201_CREATED: {
            "model": ULPINGenerateResponse,
            "description": "3D ULPIN generated and persisted into PostgreSQL/PostGIS",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ULPINErrorResponse,
            "description": "Validation error in 3D ULPIN parameters",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ULPINErrorResponse,
            "description": "Referenced unit record not found in database",
        },
        status.HTTP_409_CONFLICT: {
            "model": ULPINErrorResponse,
            "description": "Duplicate 3D ULPIN or unit already has an assigned ULPIN",
        },
    },
    summary="Generate and Optionally Persist 3D ULPIN",
    description=(
        "Deterministically generates a canonical 3D ULPIN identifier. "
        "When persistence is requested (or when a referenced unit is resolved), "
        "persists the record in PostgreSQL ulpin_3d_records."
    ),
)
def generate_ulpin(
    payload: ULPINGenerateRequest,
    response: Response,
    persist: Optional[bool] = Query(
        default=None,
        description="Explicitly control database persistence (overrides payload.persist)",
    ),
    auto_create_unit: Optional[bool] = Query(
        default=None,
        description="Auto-create cadastral unit hierarchy if missing (overrides payload.auto_create_unit)",
    ),
    db: Session = Depends(get_db),
) -> Any:
    """
    Endpoint to generate a 3D ULPIN and optionally persist to PostgreSQL/PostGIS.

    - Returns HTTP 200: Generated without persistence, or auto-created/idempotently resolved.
    - Returns HTTP 201: Successfully generated and persisted to database.
    - Returns HTTP 400: Input parameter validation error.
    - Returns HTTP 404: Referenced unit record does not exist.
    - Returns HTTP 409: Duplicate 3D ULPIN or unit already bound.
    """
    # Parse unit_id if provided
    parsed_unit_id: Optional[uuid.UUID] = None
    if payload.unit_id:
        try:
            parsed_unit_id = uuid.UUID(str(payload.unit_id).strip())
        except (ValueError, AttributeError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": f"Invalid unit_id format: '{payload.unit_id}'. Must be a valid UUID.",
                    "detail": f"Invalid unit_id format: '{payload.unit_id}'. Must be a valid UUID.",
                },
            )

    # Determine persistence and auto-creation intent
    should_auto_create = auto_create_unit if auto_create_unit is not None else payload.auto_create_unit
    should_persist = persist if persist is not None else payload.persist
    if should_auto_create:
        should_persist = True
    if should_persist is None and parsed_unit_id is not None:
        should_persist = True

    # Gracefully sanitize and normalize building, floor, unit, and property type inputs
    clean_building = payload.building
    if isinstance(clean_building, str):
        cb = clean_building.strip().upper()
        if cb.isdigit() and 1 <= len(cb) <= 3:
            clean_building = f"B{int(cb):03d}"
        elif cb.startswith("BUILDING"):
            clean_building = cb[8:].strip()

    clean_floor = payload.floor
    if isinstance(clean_floor, str):
        cf = clean_floor.strip().upper()
        if cf in ("G", "GF", "GROUND", "GROUND FLOOR", "GROUNDFLOOR"):
            clean_floor = "F00"

    clean_unit = payload.unit
    if isinstance(clean_unit, str):
        cu = clean_unit.strip().upper()
        if cu.startswith("UNIT"):
            cu = cu[4:].strip()
        if cu.startswith("U-") and cu[2:].isdigit():
            clean_unit = f"U{int(cu[2:]):03d}"
        elif cu.startswith("U ") and cu[2:].isdigit():
            clean_unit = f"U{int(cu[2:]):03d}"

    clean_type = payload.type.strip().upper()
    type_aliases = {
        "PARKING": "PRK",
        "PARKING BAY": "PRK",
        "RESIDENTIAL": "RES",
        "COMMERCIAL": "COM",
        "OFFICE": "OFF",
        "UTILITY": "UTL",
        "INFRASTRUCTURE": "UTL",
        "TERRACE": "TER",
        "INDUSTRIAL": "IND",
        "STORAGE": "STR",
        "WAREHOUSE": "STR",
        "MIXED": "MIX",
        "MIXED-USE": "MIX",
        "MIXED USE": "MIX",
    }
    if clean_type in type_aliases:
        clean_type = type_aliases[clean_type]

    try:
        # Case 0: Auto-creation of unit hierarchy and persistence requested
        if should_auto_create is True:
            ulpin, record = ensure_cadastral_unit_hierarchy(
                db,
                state=payload.state,
                district=payload.district,
                parcel=payload.parcel,
                building=clean_building,
                floor=clean_floor,
                unit=clean_unit,
                property_type=clean_type,
                unit_id=parsed_unit_id,
            )
            response.status_code = status.HTTP_200_OK
            return ULPINGenerateResponse(
                success=True,
                ulpin_3d=ulpin,
                persisted=True,
                record_id=str(record.id),
                unit_id=str(record.unit_id),
            )

        # Case 1: Persistence explicitly requested
        if should_persist is True:
            ulpin, record = create_ulpin_record(
                db,
                state=payload.state,
                district=payload.district,
                parcel=payload.parcel,
                building=clean_building,
                floor=clean_floor,
                unit=clean_unit,
                property_type=clean_type,
                unit_id=parsed_unit_id,
            )
            response.status_code = status.HTTP_201_CREATED
            return ULPINGenerateResponse(
                success=True,
                ulpin_3d=ulpin,
                persisted=True,
                record_id=str(record.id),
                unit_id=str(record.unit_id),
            )

        # Case 2: Persistence explicitly disabled
        if should_persist is False:
            ulpin = generate_3d_ulpin(
                state=payload.state,
                district=payload.district,
                parcel=payload.parcel,
                building=clean_building,
                floor=clean_floor,
                unit=clean_unit,
                property_type=clean_type,
            )
            response.status_code = status.HTTP_200_OK
            return ULPINGenerateResponse(
                success=True,
                ulpin_3d=ulpin,
                persisted=False,
            )

        # Case 3: Persistence not explicitly demanded (should_persist is None)
        # First generate the canonical identifier
        ulpin = generate_3d_ulpin(
            state=payload.state,
            district=payload.district,
            parcel=payload.parcel,
            building=clean_building,
            floor=clean_floor,
            unit=clean_unit,
            property_type=clean_type,
        )

        # Check if an authoritative cadastral Unit already exists in the database
        norm_parcel = normalize_parcel(payload.parcel)
        norm_building = normalize_building(clean_building)
        norm_floor = normalize_floor(clean_floor)
        floor_int = extract_floor_number(norm_floor)
        norm_unit = normalize_unit(clean_unit)

        unit_obj = resolve_unit(
            db,
            parcel_id=norm_parcel,
            building_id=norm_building,
            floor_number=floor_int,
            unit_code=norm_unit,
        )

        if unit_obj is not None:
            # Cadastral unit exists in the database -> persist to ulpin_3d_records
            ulpin, record = create_ulpin_record(
                db,
                state=payload.state,
                district=payload.district,
                parcel=payload.parcel,
                building=payload.building,
                floor=payload.floor,
                unit=payload.unit,
                property_type=payload.type,
                unit_id=unit_obj.id,
            )
            response.status_code = status.HTTP_201_CREATED
            return ULPINGenerateResponse(
                success=True,
                ulpin_3d=ulpin,
                persisted=True,
                record_id=str(record.id),
                unit_id=str(record.unit_id),
            )

        # Cadastral unit does not exist in DB and persistence was not demanded
        # Return pure generation result without error (Requirement 12 & 16)
        response.status_code = status.HTTP_200_OK
        return ULPINGenerateResponse(
            success=True,
            ulpin_3d=ulpin,
            persisted=False,
        )

    except ULPINValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )
    except ULPINUnitNotFoundError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )
    except ULPINDuplicateError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )


def serialize_ulpin_record(record: ULPIN3D) -> ULPINRecordData:
    """Helper to convert ORM ULPIN3D entity to clean Pydantic cadastral data without leaking ORM internals or owner PII."""
    return ULPINRecordData(
        record_id=str(record.id),
        ulpin_3d=record.ulpin_3d,
        unit_id=str(record.unit_id),
        parcel_id_reference=record.parcel_id_reference,
        building_id_reference=record.building_id_reference,
        floor_number=record.floor_number,
        unit_code=record.unit_code,
        unit_type=record.unit_type,
        generation_version=record.generation_version,
        created_at=record.created_at,
    )


@router.get(
    "/spatial/bbox",
    response_model=ULPINSpatialCollectionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINSpatialCollectionResponse,
            "description": "3D ULPIN records intersecting the bounding box",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid bounding box coordinate parameters",
        },
    },
    summary="Spatial Bounding Box Query",
    description="Returns all persisted 3D ULPIN records whose spatial geometry intersects the requested bounding box in EPSG:4326.",
)
def query_ulpins_by_bbox(
    min_lon: float = Query(..., ge=-180.0, le=180.0, description="Minimum longitude (-180.0 to 180.0)"),
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="Minimum latitude (-90.0 to 90.0)"),
    max_lon: float = Query(..., ge=-180.0, le=180.0, description="Maximum longitude (-180.0 to 180.0)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="Maximum latitude (-90.0 to 90.0)"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Queries persisted 3D ULPIN records intersecting a 2D bounding box envelope using PostGIS ST_MakeEnvelope.
    Returns HTTP 200 with matching records (empty list if none found), or HTTP 422 if coordinates/bounds are invalid.
    """
    try:
        records = find_ulpins_within_bbox(
            db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
        )
        serialized = [serialize_ulpin_record(r) for r in records]
        return ULPINSpatialCollectionResponse(
            success=True,
            data=serialized,
            count=len(serialized),
        )
    except SpatialValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )


@router.get(
    "/spatial/point",
    response_model=ULPINSpatialCollectionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINSpatialCollectionResponse,
            "description": "3D ULPIN records intersecting the horizontal XY point",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid point coordinate parameters",
        },
    },
    summary="Spatial Horizontal Point Query",
    description="Returns persisted 3D ULPIN records whose volumetric geometry intersects the requested horizontal XY point (longitude, latitude) in EPSG:4326.",
)
def query_ulpins_by_point(
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Horizontal longitude coordinate in EPSG:4326 (-180.0 to 180.0)"),
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Horizontal latitude coordinate in EPSG:4326 (-90.0 to 90.0)"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Queries persisted 3D ULPIN records intersecting a horizontal XY location using PostGIS ST_Intersects and ST_MakePoint.
    Returns HTTP 200 with matching records (empty list if none found), or HTTP 422 if coordinates are invalid.
    """
    try:
        records = find_ulpins_at_point(
            db,
            longitude=longitude,
            latitude=latitude,
        )
        serialized = [serialize_ulpin_record(r) for r in records]
        return ULPINSpatialCollectionResponse(
            success=True,
            data=serialized,
            count=len(serialized),
        )
    except SpatialValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )


@router.get(
    "/spatial/z-range",
    response_model=ULPINSpatialCollectionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINSpatialCollectionResponse,
            "description": "3D ULPIN records overlapping the vertical elevation range",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid vertical range parameters",
        },
    },
    summary="Vertical 3D Spatial Z-Range Query",
    description="Returns persisted 3D ULPIN records whose vertical 3D spatial extent overlaps the requested elevation range in meters (EPSG:4326 + Z).",
)
def query_ulpins_by_z_range(
    min_z: float = Query(..., description="Minimum vertical Z elevation in meters"),
    max_z: float = Query(..., description="Maximum vertical Z elevation in meters"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Queries persisted 3D ULPIN records overlapping a vertical Z elevation range in meters using PostGIS ST_ZMin/ST_ZMax and floor elevation datums.
    Returns HTTP 200 with matching records (empty list if none found), or HTTP 422 if min_z > max_z.
    """
    try:
        records = find_ulpins_by_height_range(
            db,
            min_z=min_z,
            max_z=max_z,
        )
        serialized = [serialize_ulpin_record(r) for r in records]
        return ULPINSpatialCollectionResponse(
            success=True,
            data=serialized,
            count=len(serialized),
        )
    except SpatialValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "success": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )


@router.get(
    "/unit/{unit_id}",
    response_model=ULPINRetrieveResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINRetrieveResponse,
            "description": "3D ULPIN record associated with the unit",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ULPINErrorResponse,
            "description": "No 3D ULPIN record exists for the specified unit",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid UUID format for unit_id",
        },
    },
    summary="Retrieve 3D ULPIN by Unit ID",
    description="Resolves and returns the canonical 3D ULPIN record associated with a given Unit UUID.",
)
def get_ulpin_by_unit(
    unit_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieves the 3D ULPIN record associated with a specific volumetric unit ID.
    Returns HTTP 200 on success, HTTP 404 if no record exists, and HTTP 422 if unit_id is not a valid UUID.
    """
    record = get_ulpin_record_by_unit_id(db, unit_id)
    if not record:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": f"3D ULPIN record not found for unit '{unit_id}'.",
                "detail": f"No 3D ULPIN record found associated with unit ID '{unit_id}'.",
            },
        )
    return ULPINRetrieveResponse(
        success=True,
        data=serialize_ulpin_record(record),
    )


@router.get(
    "/parcel/{parcel_id}",
    response_model=ULPINParcelCollectionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINParcelCollectionResponse,
            "description": "Collection of 3D ULPIN records belonging to the parcel",
        },
    },
    summary="Retrieve 3D ULPINs by Parcel",
    description="Returns all persisted 3D ULPIN records belonging to the specified parcel in deterministic order.",
)
def get_ulpins_by_parcel(
    parcel_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Returns all persisted 3D ULPIN records belonging to the specified parent parcel.
    Results are deterministically ordered. Returns an empty collection (HTTP 200) when no records exist.
    """
    records = get_ulpin_records_by_parcel(db, parcel_id)
    serialized = [serialize_ulpin_record(r) for r in records]
    return ULPINParcelCollectionResponse(
        success=True,
        data=serialized,
        count=len(serialized),
    )


@router.get(
    "/{ulpin_3d}",
    response_model=ULPINRetrieveResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ULPINRetrieveResponse,
            "description": "Persisted 3D ULPIN record",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ULPINErrorResponse,
            "description": "3D ULPIN record not found",
        },
    },
    summary="Retrieve 3D ULPIN by Canonical Identifier",
    description="Queries and returns a persisted 3D ULPIN record by its canonical alphanumeric identifier.",
)
def get_ulpin_by_code(
    ulpin_3d: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieves a single persisted 3D ULPIN record by its canonical identifier string.
    Returns HTTP 200 on success and HTTP 404 if the identifier does not exist.
    """
    record = get_ulpin_record_by_code(db, ulpin_3d)
    if not record:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": f"3D ULPIN '{ulpin_3d}' not found.",
                "detail": f"No persisted 3D ULPIN record exists matching '{ulpin_3d}'.",
            },
        )
    return ULPINRetrieveResponse(
        success=True,
        data=serialize_ulpin_record(record),
    )

