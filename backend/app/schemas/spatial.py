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


class GeometryBounds(BaseModel):
    """3D bounding box coordinates in EPSG:4326 + Z."""
    min_lon: float = Field(..., description="Minimum longitude in EPSG:4326")
    max_lon: float = Field(..., description="Maximum longitude in EPSG:4326")
    min_lat: float = Field(..., description="Minimum latitude in EPSG:4326")
    max_lat: float = Field(..., description="Maximum latitude in EPSG:4326")
    min_z: Optional[float] = Field(None, description="Minimum elevation Z in meters")
    max_z: Optional[float] = Field(None, description="Maximum elevation Z in meters")

    model_config = ConfigDict(extra="ignore")


class GeometryOrigin(BaseModel):
    """Centroid/origin coordinates for Three.js local metric translation."""
    center_lon: float = Field(..., description="Centroid longitude in EPSG:4326")
    center_lat: float = Field(..., description="Centroid latitude in EPSG:4326")
    center_z: Optional[float] = Field(None, description="Centroid elevation Z in meters")

    model_config = ConfigDict(extra="ignore")


class VerticalRange(BaseModel):
    """Vertical elevation extent in meters."""
    min_z: Optional[float] = Field(None, description="Minimum vertical Z elevation in meters")
    max_z: Optional[float] = Field(None, description="Maximum vertical Z elevation in meters")
    elevation_datum: str = Field("MSL", description="Vertical reference datum")

    model_config = ConfigDict(extra="ignore")


class BuildingGeometrySummary(BaseModel):
    """Parent building metadata and footprint geometry."""
    building_id: str
    name: Optional[str] = None
    height_m: Optional[float] = None
    total_floors: Optional[int] = None
    geometry: Optional[dict] = None

    model_config = ConfigDict(extra="ignore")


class FloorGeometrySummary(BaseModel):
    """Parent floor metadata, elevation, and boundary geometry."""
    floor_number: int
    floor_name: Optional[str] = None
    elevation_m: Optional[float] = None
    height_m: Optional[float] = None
    geometry: Optional[dict] = None

    model_config = ConfigDict(extra="ignore")


class ParcelGeometrySummary(BaseModel):
    """Parent parcel metadata and boundary geometry."""
    parcel_id: str
    state: Optional[str] = None
    district: Optional[str] = None
    geometry: Optional[dict] = None

    model_config = ConfigDict(extra="ignore")


class UnitGeometryResponse(BaseModel):
    """Response payload for authoritative PostGIS unit 3D geometry serialization."""
    success: bool = Field(True, description="Indicates serialization success")
    unit_id: str = Field(..., description="UUID of the volumetric property unit")
    srid: int = Field(4326, description="Spatial reference system identifier (EPSG:4326)")
    geometry_type: Optional[str] = Field(None, description="Geometry type e.g. PolyhedralSurface, Polygon, MultiPolygon")
    has_geometry: bool = Field(..., description="Whether unit has a registered PostGIS geometry")
    geometry: Optional[dict] = Field(None, description="Standard GeoJSON 3D geometry object with [lon, lat, elev] coordinates")
    building: Optional[BuildingGeometrySummary] = Field(None, description="Parent building footprint and elevation")
    floor: Optional[FloorGeometrySummary] = Field(None, description="Parent floor boundary and elevation")
    parcel: Optional[ParcelGeometrySummary] = Field(None, description="Parent cadastral parcel boundary")
    bounds: Optional[GeometryBounds] = Field(None, description="3D bounding box coordinates")
    vertical_range: Optional[VerticalRange] = Field(None, description="Vertical elevation range in meters")
    origin: Optional[GeometryOrigin] = Field(None, description="Local coordinate origin for 3D rendering")
    source: str = Field("postgis", description="Authoritative spatial data source")
    message: str = Field("Authoritative PostGIS geometry serialized successfully.", description="Status message")
    detail: Optional[str] = Field(None, description="Additional context or notes")

    model_config = ConfigDict(extra="ignore")

