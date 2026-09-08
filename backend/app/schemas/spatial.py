from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SpatialChecks(BaseModel):
    """
    Boolean breakdown of spatial validity and hierarchy containment checks.
    """
    unit_geometry_valid: bool = Field(
        ...,
        description="True if unit 3D geometry is valid according to PostGIS ST_IsValid and has SRID 4326",
    )
    floor_geometry_valid: bool = Field(
        ...,
        description="True if floor geometry is valid or safely handled when omitted",
    )
    building_geometry_valid: bool = Field(
        ...,
        description="True if building footprint geometry is valid according to PostGIS ST_IsValid and has SRID 4326",
    )
    building_within_parcel: bool = Field(
        ...,
        description="True if building footprint is spatially contained within parent parcel boundary",
    )
    unit_within_parent: bool = Field(
        ...,
        description="True if unit geometry is spatially contained within parent floor or building footprint",
    )

    model_config = ConfigDict(extra="ignore")


class UnitSpatialValidationResponse(BaseModel):
    """
    Response payload for successful spatial validation (HTTP 200).
    """
    success: bool = Field(True, description="Indicates the validation request was processed successfully")
    valid: bool = Field(..., description="Indicates whether all spatial hierarchy checks passed")
    unit_id: str = Field(..., description="UUID of the validated volumetric unit")
    checks: SpatialChecks = Field(..., description="Detailed boolean breakdown of individual spatial checks")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        json_schema_extra={
            "example": {
                "success": True,
                "valid": True,
                "unit_id": "c1f7b4e2-8924-4d89-9a28-98e3b1c1e555",
                "checks": {
                    "unit_geometry_valid": True,
                    "floor_geometry_valid": True,
                    "building_geometry_valid": True,
                    "building_within_parcel": True,
                    "unit_within_parent": True,
                },
            }
        },
    )


class SpatialValidationErrorResponse(BaseModel):
    """
    Response payload for spatial validation failures (HTTP 400).
    """
    success: bool = Field(False, description="Indicates validation failure")
    valid: bool = Field(False, description="Spatial hierarchy is invalid")
    unit_id: Optional[str] = Field(None, description="UUID of the unit, if available")
    error: str = Field(..., description="Primary error message")
    detail: str = Field(..., description="Detailed explanation of the validation failure")
    checks: Optional[SpatialChecks] = Field(None, description="Breakdown of checks completed before failure")

    model_config = ConfigDict(extra="ignore")
