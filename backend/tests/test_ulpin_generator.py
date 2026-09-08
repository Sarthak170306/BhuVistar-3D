"""
Unit tests for the 3D ULPIN Generator Service.

Verifies canonical format, normalization, validation, determinism, and uniqueness
in accordance with docs/architecture/3d_ulpin_specification.md.
"""

import pytest
from app.services.ulpin_generator import (
    ULPINValidationError,
    generate_3d_ulpin,
    normalize_building,
    normalize_district,
    normalize_floor,
    normalize_parcel,
    normalize_property_type,
    normalize_state,
    normalize_unit,
)


def test_residential_apartment():
    """1. Test residential apartment canonical generation."""
    ulpin = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor=4,
        unit=402,
        property_type="RES",
    )
    assert ulpin == "BV3D-UP-LKO-12345678-B001-F04-U402-RES"


def test_ground_floor_shop():
    """2. Test ground-floor commercial shop generation."""
    ulpin = generate_3d_ulpin(
        state="KA",
        district="BLR",
        parcel="87654321",
        building="B002",
        floor="F00",
        unit="U012",
        property_type="COM",
    )
    assert ulpin == "BV3D-KA-BLR-87654321-B002-F00-U012-COM"


def test_basement_parking():
    """3. Test basement parking bay generation."""
    ulpin = generate_3d_ulpin(
        state="UP",
        district="NOI",
        parcel="55443322",
        building="B001",
        floor="B02",
        unit="UP45",
        property_type="PRK",
    )
    assert ulpin == "BV3D-UP-NOI-55443322-B001-B02-UP45-PRK"


def test_basement_storage():
    """4. Test basement storage bay generation."""
    ulpin = generate_3d_ulpin(
        state="DL",
        district="DEL",
        parcel="11223344",
        building="B001",
        floor="B01",
        unit="US05",
        property_type="STR",
    )
    assert ulpin == "BV3D-DL-DEL-11223344-B001-B01-US05-STR"


def test_terrace_floor():
    """5. Test valid terrace floor (Txx)."""
    ulpin = generate_3d_ulpin(
        state="MH",
        district="PUN",
        parcel="33445566",
        building="B003",
        floor="T14",
        unit="U14T",
        property_type="TER",
    )
    assert ulpin == "BV3D-MH-PUN-33445566-B003-T14-U14T-TER"

    # Also test roof level T00
    ulpin_roof = generate_3d_ulpin(
        state="MH",
        district="PUN",
        parcel="33445566",
        building="B003",
        floor="T00",
        unit="U001",
        property_type="TER",
    )
    assert ulpin_roof == "BV3D-MH-PUN-33445566-B003-T00-U001-TER"


def test_mezzanine_floor():
    """6. Test valid mezzanine floor (Mxx)."""
    ulpin = generate_3d_ulpin(
        state="KA",
        district="BLR",
        parcel="99887766",
        building="B001",
        floor="M01",
        unit="U001",
        property_type="OFF",
    )
    assert ulpin == "BV3D-KA-BLR-99887766-B001-M01-U001-OFF"


def test_podium_floor():
    """7. Test valid podium floor (Pxx)."""
    ulpin = generate_3d_ulpin(
        state="MH",
        district="MUM",
        parcel="12121212",
        building="B001",
        floor="P02",
        unit="UP01",
        property_type="PRK",
    )
    assert ulpin == "BV3D-MH-MUM-12121212-B001-P02-UP01-PRK"


def test_lowercase_normalization():
    """8. Test automatic normalization of lowercase inputs."""
    ulpin = generate_3d_ulpin(
        state="up",
        district="lko",
        parcel="12345678",
        building="b001",
        floor="f04",
        unit="u402",
        property_type="res",
    )
    assert ulpin == "BV3D-UP-LKO-12345678-B001-F04-U402-RES"


def test_whitespace_normalization():
    """9. Test automatic stripping of leading and trailing whitespace."""
    ulpin = generate_3d_ulpin(
        state="  UP  ",
        district=" LKO ",
        parcel=" 12345678 ",
        building=" B001 ",
        floor=" F04 ",
        unit=" U402 ",
        property_type=" RES ",
    )
    assert ulpin == "BV3D-UP-LKO-12345678-B001-F04-U402-RES"


def test_invalid_state():
    """10. Test invalid state rejection."""
    for invalid in ["U", "UPP", "12", "", "U-", "UttarPradesh"]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state=invalid,
                district="LKO",
                parcel="12345678",
                building="B001",
                floor=4,
                unit=402,
                property_type="RES",
            )


def test_invalid_district():
    """11. Test invalid district rejection."""
    for invalid in ["LK", "LUCK", "123", "", "L-O"]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district=invalid,
                parcel="12345678",
                building="B001",
                floor=4,
                unit=402,
                property_type="RES",
            )


def test_invalid_parcel():
    """12. Test invalid parcel length and format rejection."""
    for invalid in ["123", "1234567", "123456789012345", "", "1234-5678"]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district="LKO",
                parcel=invalid,
                building="B001",
                floor=4,
                unit=402,
                property_type="RES",
            )


def test_invalid_building():
    """13. Test invalid building format rejection."""
    for invalid in ["Tower", "001", "B0001", "", "B-01", 1000]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district="LKO",
                parcel="12345678",
                building=invalid,
                floor=4,
                unit=402,
                property_type="RES",
            )


def test_invalid_floor():
    """14. Test invalid floor codes rejection."""
    for invalid in ["XYZ", "F100", 100, -100, "B00", "M00", "P00", "", "--4"]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district="LKO",
                parcel="12345678",
                building="B001",
                floor=invalid,
                unit=402,
                property_type="RES",
            )


def test_invalid_unit():
    """15. Test invalid unit code rejection."""
    for invalid in ["INVALID_UNIT", "", "U1234", "U-01", 1000, -1]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district="LKO",
                parcel="12345678",
                building="B001",
                floor=4,
                unit=invalid,
                property_type="RES",
            )


def test_invalid_property_type():
    """16. Test unsupported property type rejection."""
    for invalid in ["XYZ", "HOUSE", "VILLA", "", "COMMERCIAL", "FLAT"]:
        with pytest.raises(ULPINValidationError):
            generate_3d_ulpin(
                state="UP",
                district="LKO",
                parcel="12345678",
                building="B001",
                floor=4,
                unit=402,
                property_type=invalid,
            )


def test_determinism():
    """17. Test that identical inputs consistently yield the exact same ULPIN."""
    ulpin1 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor=4,
        unit=402,
        property_type="RES",
    )
    ulpin2 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor=4,
        unit=402,
        property_type="RES",
    )
    assert ulpin1 == ulpin2
    assert ulpin1 == "BV3D-UP-LKO-12345678-B001-F04-U402-RES"


def test_different_floor_produces_different_ulpin():
    """18. Test that changing floor produces distinct ULPINs."""
    ulpin_f03 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor=3,
        unit="U012",
        property_type="RES",
    )
    ulpin_f04 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor=4,
        unit="U012",
        property_type="RES",
    )
    assert ulpin_f03 != ulpin_f04
    assert ulpin_f03 == "BV3D-UP-LKO-12345678-B001-F03-U012-RES"
    assert ulpin_f04 == "BV3D-UP-LKO-12345678-B001-F04-U012-RES"


def test_different_unit_produces_different_ulpin():
    """19. Test that changing unit produces distinct ULPINs."""
    ulpin_u12 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor="F03",
        unit="U012",
        property_type="RES",
    )
    ulpin_u13 = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor="F03",
        unit="U013",
        property_type="RES",
    )
    assert ulpin_u12 != ulpin_u13
    assert ulpin_u12 == "BV3D-UP-LKO-12345678-B001-F03-U012-RES"
    assert ulpin_u13 == "BV3D-UP-LKO-12345678-B001-F03-U013-RES"


def test_different_property_type_produces_different_ulpin():
    """20. Test that changing property type produces distinct ULPINs."""
    ulpin_res = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor="F03",
        unit="U012",
        property_type="RES",
    )
    ulpin_com = generate_3d_ulpin(
        state="UP",
        district="LKO",
        parcel="12345678",
        building="B001",
        floor="F03",
        unit="U012",
        property_type="COM",
    )
    assert ulpin_res != ulpin_com
    assert ulpin_res == "BV3D-UP-LKO-12345678-B001-F03-U012-RES"
    assert ulpin_com == "BV3D-UP-LKO-12345678-B001-F03-U012-COM"
