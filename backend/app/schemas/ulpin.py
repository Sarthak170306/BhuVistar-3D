from typing import Optional, Union
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ULPINGenerateRequest(BaseModel):
    """
    Request payload schema for generating a deterministic 3D ULPIN.
    """
    state: str = Field(
        ...,
        description="2-letter Indian state code (e.g. UP, DL, KA)",
        examples=["UP"],
    )
    district: str = Field(
        ...,
        description="3-letter district abbreviation (e.g. NOI, LKO, BLR)",
        examples=["NOI"],
    )
    parcel: str = Field(
        ...,
        description="8-14 character cadastral parcel ID or 2D ULPIN (e.g. 55443322)",
        examples=["55443322"],
    )
    building: Union[str, int] = Field(
        ...,
        description="Building code or integer index (e.g. B001, 1)",
        examples=["B001"],
    )
    floor: Union[str, int] = Field(
        ...,
        description="Floor code or level integer (e.g. B02, F04, 4, -2)",
        examples=["B02"],
    )
    unit: Union[str, int] = Field(
        ...,
        description="Unit code or integer number (e.g. UP32, U012, 402)",
        examples=["UP32"],
    )
    type: str = Field(
        ...,
        validation_alias=AliasChoices("type", "property_type", "unit_type"),
        description="3-letter property type classification code (e.g. PRK, RES, COM)",
        examples=["PRK"],
    )
    unit_id: Optional[str] = Field(
        default=None,
        description="Optional UUID of existing Unit entity to associate directly",
        examples=["c1f7b4e2-8924-4d89-9a28-98e3b1c1e555"],
    )
    persist: Optional[bool] = Field(
        default=None,
        description="Set True to persist to database, False for pure generation without persistence",
        examples=[True],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "state": "UP",
                "district": "NOI",
                "parcel": "55443322",
                "building": "B001",
                "floor": "B02",
                "unit": "UP32",
                "type": "PRK",
            }
        },
    )


class ULPINGenerateResponse(BaseModel):
    """
    Successful 3D ULPIN generation response.
    """
    success: bool = Field(
        default=True,
        description="Indicates whether 3D ULPIN generation succeeded",
    )
    ulpin_3d: str = Field(
        ...,
        description="Canonical 3D ULPIN identifier",
        examples=["BV3D-UP-NOI-55443322-B001-B02-UP32-PRK"],
    )
    persisted: bool = Field(
        default=False,
        description="Indicates whether the ULPIN record was committed to PostgreSQL/PostGIS",
        examples=[True],
    )
    record_id: Optional[str] = Field(
        default=None,
        description="UUID primary key of the persisted ulpin_3d_records entity",
        examples=["d3a1b5c2-1234-4567-89ab-cdef01234567"],
    )
    unit_id: Optional[str] = Field(
        default=None,
        description="UUID primary key of the associated Unit entity in the units table",
        examples=["c1f7b4e2-8924-4d89-9a28-98e3b1c1e555"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "ulpin_3d": "BV3D-UP-NOI-55443322-B001-B02-UP32-PRK",
                "persisted": True,
                "record_id": "d3a1b5c2-1234-4567-89ab-cdef01234567",
                "unit_id": "c1f7b4e2-8924-4d89-9a28-98e3b1c1e555",
            }
        }
    )


class ULPINErrorResponse(BaseModel):
    """
    Error response schema for validation failures.
    """
    success: bool = Field(
        default=False,
        description="Indicates generation failure",
    )
    error: str = Field(
        ...,
        description="Human-readable error description explaining the validation failure",
    )
    detail: Optional[str] = Field(
        default=None,
        description="Detailed validation error message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "State must contain exactly 2 uppercase alphabetic characters.",
                "detail": "State must contain exactly 2 uppercase alphabetic characters.",
            }
        }
    )
