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
    extract_floor_number,
    get_ulpin_record_by_code,
    get_ulpin_record_by_unit_id,
    get_ulpin_records_by_parcel,
    resolve_unit,
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
    db: Session = Depends(get_db),
) -> Any:
    """
    Endpoint to generate a 3D ULPIN and optionally persist to PostgreSQL/PostGIS.

    - Returns HTTP 200: Generated without persistence.
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

    # Determine persistence intent
    should_persist = persist if persist is not None else payload.persist
    if should_persist is None and parsed_unit_id is not None:
        should_persist = True

    try:
        # Case 1: Persistence explicitly requested
        if should_persist is True:
            ulpin, record = create_ulpin_record(
                db,
                state=payload.state,
                district=payload.district,
                parcel=payload.parcel,
                building=payload.building,
                floor=payload.floor,
                unit=payload.unit,
                property_type=payload.type,
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
                building=payload.building,
                floor=payload.floor,
                unit=payload.unit,
                property_type=payload.type,
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
            building=payload.building,
            floor=payload.floor,
            unit=payload.unit,
            property_type=payload.type,
        )

        # Check if an authoritative cadastral Unit already exists in the database
        norm_parcel = normalize_parcel(payload.parcel)
        norm_building = normalize_building(payload.building)
        norm_floor = normalize_floor(payload.floor)
        floor_int = extract_floor_number(norm_floor)
        norm_unit = normalize_unit(payload.unit)

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

