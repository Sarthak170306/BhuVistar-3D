import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.unit import Unit
from app.schemas.spatial import (
    SpatialChecks,
    SpatialValidationErrorResponse,
    UnitSpatialValidationResponse,
)
from app.services.spatial_validation_service import (
    InvalidGeometryError,
    SpatialContainmentError,
    SpatialValidationError,
    validate_unit_spatial_hierarchy,
)
from app.services.ulpin_record_service import ULPINUnitNotFoundError

router = APIRouter()


@router.api_route(
    "/validate-unit/{unit_id}",
    methods=["POST", "GET"],
    response_model=UnitSpatialValidationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": UnitSpatialValidationResponse,
            "description": "Spatial hierarchy validation succeeded and is valid",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": SpatialValidationErrorResponse,
            "description": "Invalid spatial relationship, invalid geometry, or malformed UUID",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Unit not found in database",
        },
    },
    summary="Validate 3D Unit Spatial Hierarchy",
    description="Validates spatial containment and geometric validity for Parcel -> Building -> Floor -> Unit hierarchy using PostGIS.",
)
def validate_unit_hierarchy_endpoint(
    unit_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Validates spatial containment and geometric validity for a volumetric property unit hierarchy.

    Verifies:
    1. Building footprint is spatially contained within parent parcel boundary.
    2. Floor geometry is spatially contained within parent building footprint when both geometries exist.
    3. Unit geometry is spatially contained within parent floor/building footprint.
    4. Geometries are valid according to PostGIS ST_IsValid.
    5. Geometries have expected SRID 4326.
    6. Safe handling of omitted floor geometries.
    7. No owner PII is exposed.
    """
    # 1. Parse and validate UUID format
    try:
        unit_uuid = uuid.UUID(unit_id)
    except (ValueError, AttributeError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "valid": False,
                "error": f"Invalid unit UUID format: '{unit_id}'.",
                "detail": f"The provided unit ID '{unit_id}' is not a valid UUID.",
            },
        )

    # 2. Check Unit existence
    unit = db.query(Unit).filter(Unit.id == unit_uuid).first()
    if not unit:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "valid": False,
                "error": f"Unit '{unit_id}' not found.",
                "detail": f"No unit found matching ID '{unit_id}' in the database.",
            },
        )

    # 3. Perform spatial validation
    try:
        result = validate_unit_spatial_hierarchy(db, unit_uuid, raise_on_error=False)

        if not result["valid"]:
            error_msg = result["errors"][0] if result["errors"] else "Spatial hierarchy validation failed."
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "valid": False,
                    "unit_id": str(unit_uuid),
                    "error": error_msg,
                    "detail": error_msg,
                    "checks": result["checks"],
                },
            )

        return UnitSpatialValidationResponse(
            success=True,
            valid=True,
            unit_id=str(unit_uuid),
            checks=SpatialChecks(**result["checks"]),
        )

    except (InvalidGeometryError, SpatialContainmentError, SpatialValidationError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "valid": False,
                "unit_id": str(unit_uuid),
                "error": str(exc),
                "detail": str(exc),
            },
        )
    except ULPINUnitNotFoundError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "valid": False,
                "error": str(exc),
                "detail": str(exc),
            },
        )
