"""
3D ULPIN (Unique Land Parcel Identification Number) Generator Service.

Implements the official technical specification documented in:
docs/architecture/3d_ulpin_specification.md

Format:
BV3D-{STATE}-{DISTRICT}-{PARCEL}-{BUILDING}-{FLOOR}-{UNIT}-{TYPE}
Example:
BV3D-UP-LKO-12345678-B001-F04-U402-RES
"""

import re
from typing import Final, Union

# Strict Canonical Regex Pattern
ULPIN_REGEX_PATTERN: Final[str] = (
    r"^BV3D-[A-Z]{2}-[A-Z]{3}-[A-Z0-9]{8,14}-B[A-Z0-9]{3}-[FBMTP][0-9]{2}-U[A-Z0-9]{3}-[A-Z]{3}$"
)
ULPIN_REGEX: Final[re.Pattern[str]] = re.compile(ULPIN_REGEX_PATTERN)

# Approved Volumetric Property Types
ALLOWED_PROPERTY_TYPES: Final[frozenset[str]] = frozenset({
    "RES",  # Residential (Flat, Apartment, Penthouse, Duplex)
    "COM",  # Commercial Retail (Shop, Showroom)
    "OFF",  # Commercial Office
    "PRK",  # Dedicated Parking Bay
    "IND",  # Industrial
    "STR",  # Storage / Warehouse
    "UTL",  # Utility / Infrastructure
    "TER",  # Private Volumetric Terrace / Roof Right
    "MIX",  # Mixed-use
})

# Allowed Vertical Level Classification Prefixes
ALLOWED_FLOOR_PREFIXES: Final[frozenset[str]] = frozenset({
    "F",  # Floor (Above-ground / Ground F00)
    "B",  # Basement (Sub-surface B01..B99)
    "M",  # Mezzanine (Intermediate M01..M99)
    "P",  # Podium (Elevated P01..P99)
    "T",  # Terrace / Rooftop (T00..T99)
})


class ULPINValidationError(ValueError):
    """Exception raised when an input component or the assembled 3D ULPIN fails validation."""
    pass


def normalize_state(state: str) -> str:
    """
    Validates and normalizes the 2-letter state code.
    Must contain exactly 2 uppercase alphabetic characters (ISO 3166-2:IN / Census).
    """
    if not isinstance(state, str):
        raise ULPINValidationError(f"State must be a string, got {type(state).__name__}.")
    cleaned = state.strip().upper()
    if not cleaned:
        raise ULPINValidationError("State must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("State must not contain hyphens.")
    if not re.match(r"^[A-Z]{2}$", cleaned):
        raise ULPINValidationError("State must contain exactly 2 uppercase alphabetic characters.")
    return cleaned


def normalize_district(district: str) -> str:
    """
    Validates and normalizes the 3-letter district abbreviation.
    Must contain exactly 3 uppercase alphabetic characters.
    """
    if not isinstance(district, str):
        raise ULPINValidationError(f"District must be a string, got {type(district).__name__}.")
    cleaned = district.strip().upper()
    if not cleaned:
        raise ULPINValidationError("District must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("District must not contain hyphens.")
    if not re.match(r"^[A-Z]{3}$", cleaned):
        raise ULPINValidationError("District must contain exactly 3 uppercase alphabetic characters.")
    return cleaned


def normalize_parcel(parcel: str) -> str:
    """
    Validates and normalizes the 2D parcel / survey number or Indian 2D ULPIN.
    Must contain 8 to 14 uppercase alphanumeric characters.
    """
    if not isinstance(parcel, str):
        raise ULPINValidationError(f"Parcel must be a string, got {type(parcel).__name__}.")
    cleaned = parcel.strip().upper()
    if not cleaned:
        raise ULPINValidationError("Parcel must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("Parcel must not contain hyphens.")
    if not re.match(r"^[A-Z0-9]{8,14}$", cleaned):
        raise ULPINValidationError("Parcel must contain 8–14 uppercase alphanumeric characters.")
    return cleaned


def normalize_building(building: Union[str, int]) -> str:
    """
    Validates and normalizes the building identifier.
    Must follow the Bxxx format (prefix 'B' followed by 3 alphanumeric characters).
    Numeric inputs are automatically zero-padded (e.g. 1 -> B001, B1 -> B001).
    """
    if isinstance(building, int):
        if not (1 <= building <= 999):
            raise ULPINValidationError(f"Building integer value must be between 1 and 999, got {building}.")
        return f"B{building:03d}"

    if not isinstance(building, str):
        raise ULPINValidationError(f"Building must be a string or integer, got {type(building).__name__}.")

    cleaned = building.strip().upper()
    if not cleaned:
        raise ULPINValidationError("Building must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("Building must not contain hyphens.")

    # Prefix 'B' followed by digits (e.g. "B1" -> "B001", "B001" -> "B001")
    if cleaned.startswith("B") and cleaned[1:].isdigit() and 1 <= len(cleaned[1:]) <= 3:
        num = int(cleaned[1:])
        if 1 <= num <= 999:
            return f"B{num:03d}"

    # Alpha / alphanumeric building codes (e.g. "BT0C", "BWNG", "B00A")
    if re.match(r"^B[A-Z0-9]{3}$", cleaned):
        return cleaned

    raise ULPINValidationError(f"Building must follow Bxxx format, got '{building}'.")


def normalize_floor(floor: Union[str, int]) -> str:
    """
    Validates and normalizes the floor / vertical level identifier into 3 characters.
    Supports:
      - Ground: F00 (or floor=0)
      - Above ground: F01..F99 (or positive integer 1..99)
      - Basements: B01..B99 (or negative integer -1..-99)
      - Mezzanine: M01..M99
      - Podium: P01..P99
      - Terrace: T00..T99
    """
    if isinstance(floor, int):
        if floor == 0:
            return "F00"
        elif 1 <= floor <= 99:
            return f"F{floor:02d}"
        elif -99 <= floor <= -1:
            return f"B{abs(floor):02d}"
        else:
            raise ULPINValidationError(f"Invalid floor code: Integer floor must be between -99 and 99, got {floor}.")

    if not isinstance(floor, str):
        raise ULPINValidationError(f"Floor must be a string or integer, got {type(floor).__name__}.")

    cleaned = floor.strip().upper()
    if not cleaned:
        raise ULPINValidationError("Floor must not be empty.")
    if "--" in cleaned:
        raise ULPINValidationError("Floor must not contain repeated hyphens.")

    # Try parsing pure numeric string e.g. "4", "0", "-2"
    try:
        val = int(cleaned)
        return normalize_floor(val)
    except ValueError:
        pass

    # Handle ground floor aliases (e.g. G, GF, GROUND, GROUNDFLOOR)
    if cleaned in ("G", "GF", "GROUND", "GROUNDFLOOR"):
        return "F00"

    if "-" in cleaned:
        raise ULPINValidationError(f"Invalid floor code: '{floor}'.")

    # Handle prefixed floor codes: F, B, M, P, T
    if len(cleaned) in (2, 3) and cleaned[0] in ALLOWED_FLOOR_PREFIXES and cleaned[1:].isdigit():
        prefix = cleaned[0]
        num = int(cleaned[1:])
        if not (0 <= num <= 99):
            raise ULPINValidationError(f"Invalid floor code: Level number must be between 0 and 99, got '{floor}'.")
        # Basements, Mezzanines, and Podiums cannot be 00 (e.g. B00 is invalid)
        if prefix in ("B", "M", "P") and num == 0:
            raise ULPINValidationError(f"Invalid floor code: {prefix} level must be between 01 and 99, got '{floor}'.")
        return f"{prefix}{num:02d}"

    raise ULPINValidationError(f"Invalid floor code: '{floor}'.")


def normalize_unit(unit: Union[str, int]) -> str:
    """
    Validates and normalizes the volumetric unit code into 4 characters (Uxxx).
    Supports numeric units (402 -> U402, 12 -> U012) and alphanumeric codes (UP45, US05, UA01).
    """
    if isinstance(unit, int):
        if not (0 <= unit <= 999):
            raise ULPINValidationError(f"Numeric unit must be between 0 and 999, got {unit}.")
        return f"U{unit:03d}"

    if not isinstance(unit, str):
        raise ULPINValidationError(f"Unit must be a string or integer, got {type(unit).__name__}.")

    cleaned = unit.strip().upper()
    if not cleaned:
        raise ULPINValidationError("Unit must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("Unit must not contain hyphens.")

    # Pure digits e.g. "12" -> "U012", "402" -> "U402"
    if cleaned.isdigit() and 1 <= len(cleaned) <= 3:
        return f"U{int(cleaned):03d}"

    # Prefix 'U' with 1, 2, or 3 digits e.g. "U12" -> "U012", "U4" -> "U004", "U001" -> "U001"
    if cleaned.startswith("U") and cleaned[1:].isdigit() and 1 <= len(cleaned[1:]) <= 3:
        return f"U{int(cleaned[1:]):03d}"

    # Exactly 4 characters starting with 'U' + 3 alphanumeric characters
    if len(cleaned) == 4 and cleaned.startswith("U") and cleaned[1:].isalnum():
        return cleaned

    # 3-character alphanumeric unit code (e.g. "F01" -> "UF01", "C01" -> "UC01", "P32" -> "UP32")
    if len(cleaned) == 3 and cleaned.isalnum():
        return f"U{cleaned}"

    raise ULPINValidationError(
        f"Invalid unit code: '{unit}'. Unit must follow Uxxx format (1 'U' + 3 alphanumeric characters)."
    )


def normalize_property_type(property_type: str) -> str:
    """
    Validates and normalizes the property classification code against approved types.
    Approved types: RES, COM, OFF, PRK, IND, STR, UTL, TER, MIX.
    """
    if not isinstance(property_type, str):
        raise ULPINValidationError(f"Property type must be a string, got {type(property_type).__name__}.")
    cleaned = property_type.strip().upper()
    if not cleaned:
        raise ULPINValidationError("Property type must not be empty.")
    if "-" in cleaned:
        raise ULPINValidationError("Property type must not contain hyphens.")
    if cleaned not in ALLOWED_PROPERTY_TYPES:
        raise ULPINValidationError(f"Unsupported property type: {property_type}.")
    return cleaned


def generate_3d_ulpin(
    state: str,
    district: str,
    parcel: str,
    building: Union[str, int],
    floor: Union[str, int],
    unit: Union[str, int],
    property_type: str,
) -> str:
    """
    Generates a deterministic, canonical 3D Unique Land Parcel Identification Number (3D ULPIN).

    Canonical Format:
    BV3D-{STATE}-{DISTRICT}-{PARCEL}-{BUILDING}-{FLOOR}-{UNIT}-{TYPE}

    Example:
    BV3D-UP-LKO-12345678-B001-F04-U402-RES

    Raises:
        ULPINValidationError: If any component is invalid, missing, or fails canonical validation.
    """
    norm_state = normalize_state(state)
    norm_district = normalize_district(district)
    norm_parcel = normalize_parcel(parcel)
    norm_building = normalize_building(building)
    norm_floor = normalize_floor(floor)
    norm_unit = normalize_unit(unit)
    norm_type = normalize_property_type(property_type)

    ulpin = (
        f"BV3D-{norm_state}-{norm_district}-{norm_parcel}-"
        f"{norm_building}-{norm_floor}-{norm_unit}-{norm_type}"
    )

    if not ULPIN_REGEX.match(ulpin):
        raise ULPINValidationError(f"Generated ULPIN '{ulpin}' failed canonical regex validation.")

    return ulpin
