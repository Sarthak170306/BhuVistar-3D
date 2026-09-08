import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit
from app.services.ulpin_generator import ULPINValidationError
from app.services.ulpin_record_service import (
    ULPINDuplicateError,
    ULPINUnitNotFoundError,
    create_ulpin_record,
    extract_floor_number,
    get_ulpin_record_by_code,
    get_ulpin_record_by_unit_id,
)

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture that cleans up test records."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cadastral_hierarchy(db: Session):
    """
    Creates a clean, authoritative test cadastral hierarchy in PostgreSQL:
    Parcel -> Building -> Floor -> Unit
    Cleans up all created records after the test completes.
    """
    parcel_ref = f"TEST{uuid.uuid4().hex[:8].upper()}"

    parcel = Parcel(
        parcel_id=parcel_ref,
        state="UP",
        district="NOI",
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B001",
        parcel_id=parcel.id,
        name="Tech Park Tower A",
    )
    db.add(building)
    db.flush()

    floor_basement = Floor(
        building_id=building.id,
        floor_number=-2,
        floor_name="Basement Level 2",
    )
    floor_upper = Floor(
        building_id=building.id,
        floor_number=4,
        floor_name="4th Floor",
    )
    db.add_all([floor_basement, floor_upper])
    db.flush()

    unit_parking = Unit(
        building_id=building.id,
        floor_id=floor_basement.id,
        unit_code="UP32",
        unit_type="PRK",
    )
    unit_apartment = Unit(
        building_id=building.id,
        floor_id=floor_upper.id,
        unit_code="U402",
        unit_type="RES",
    )
    db.add_all([unit_parking, unit_apartment])
    db.commit()

    yield {
        "parcel": parcel,
        "building": building,
        "floor_basement": floor_basement,
        "floor_upper": floor_upper,
        "unit_parking": unit_parking,
        "unit_apartment": unit_apartment,
    }

    # Teardown: Remove ULPIN records first, then cascade delete Parcel
    db.query(ULPIN3D).filter(
        ULPIN3D.parcel_id_reference == parcel.parcel_id
    ).delete()
    db.query(Unit).filter(
        Unit.id.in_([unit_parking.id, unit_apartment.id])
    ).delete()
    db.query(Floor).filter(
        Floor.id.in_([floor_basement.id, floor_upper.id])
    ).delete()
    db.query(Building).filter(Building.id == building.id).delete()
    db.query(Parcel).filter(Parcel.id == parcel.id).delete()
    db.commit()


def test_extract_floor_number():
    """Verify conversion of floor representations to integers."""
    assert extract_floor_number("B02") == -2
    assert extract_floor_number("B01") == -1
    assert extract_floor_number("F00") == 0
    assert extract_floor_number("F04") == 4
    assert extract_floor_number("M01") == 1
    assert extract_floor_number("P02") == 2
    assert extract_floor_number("T05") == 5
    assert extract_floor_number(4) == 4
    assert extract_floor_number(-2) == -2


def test_create_ulpin_record_service(db: Session, cadastral_hierarchy):
    """
    Test direct invocation of the create_ulpin_record service function.
    """
    hierarchy = cadastral_hierarchy
    parcel = hierarchy["parcel"]
    unit_p = hierarchy["unit_parking"]

    ulpin_code, record = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel.parcel_id,
        building="B001",
        floor="B02",
        unit="UP32",
        property_type="PRK",
    )

    expected_ulpin = f"BV3D-UP-NOI-{parcel.parcel_id}-B001-B02-UP32-PRK"
    assert ulpin_code == expected_ulpin
    assert record.id is not None
    assert record.unit_id == unit_p.id
    assert record.ulpin_3d == expected_ulpin
    assert record.parcel_id_reference == parcel.parcel_id
    assert record.floor_number == -2
    assert record.unit_code == "UP32"
    assert record.unit_type == "PRK"

    # Test lookup helpers
    by_code = get_ulpin_record_by_code(db, expected_ulpin)
    assert by_code is not None
    assert by_code.id == record.id

    by_unit = get_ulpin_record_by_unit_id(db, unit_p.id)
    assert by_unit is not None
    assert by_unit.id == record.id


def test_create_ulpin_record_duplicate_raises_conflict(db: Session, cadastral_hierarchy):
    """
    Test that calling create_ulpin_record on an existing record raises ULPINDuplicateError.
    """
    hierarchy = cadastral_hierarchy
    parcel = hierarchy["parcel"]

    # First call creates record
    create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel.parcel_id,
        building="B001",
        floor="B02",
        unit="UP32",
        property_type="PRK",
    )

    # Second call must raise duplicate conflict
    with pytest.raises(ULPINDuplicateError):
        create_ulpin_record(
            db,
            state="UP",
            district="NOI",
            parcel=parcel.parcel_id,
            building="B001",
            floor="B02",
            unit="UP32",
            property_type="PRK",
        )


def test_create_ulpin_record_unit_not_found(db: Session):
    """
    Test that referencing a non-existent unit raises ULPINUnitNotFoundError.
    """
    with pytest.raises(ULPINUnitNotFoundError):
        create_ulpin_record(
            db,
            state="UP",
            district="NOI",
            parcel="NONEXIST99",
            building="B001",
            floor="B02",
            unit="UP32",
            property_type="PRK",
        )


def test_api_persist_ulpin_success(db: Session, cadastral_hierarchy):
    """
    Test POST /api/v1/ulpin/generate with persist=True successfully
    persisting into ulpin_3d_records and returning HTTP 201.
    """
    hierarchy = cadastral_hierarchy
    parcel = hierarchy["parcel"]
    unit_p = hierarchy["unit_parking"]

    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": parcel.parcel_id,
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
        "persist": True,
    }

    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["persisted"] is True
    expected_ulpin = f"BV3D-UP-NOI-{parcel.parcel_id}-B001-B02-UP32-PRK"
    assert data["ulpin_3d"] == expected_ulpin
    assert data["unit_id"] == str(unit_p.id)
    assert data["record_id"] is not None

    # Verify directly in PostgreSQL
    persisted_record = db.query(ULPIN3D).filter(ULPIN3D.ulpin_3d == expected_ulpin).first()
    assert persisted_record is not None
    assert str(persisted_record.id) == data["record_id"]
    assert persisted_record.unit_id == unit_p.id
    assert persisted_record.parcel_id_reference == parcel.parcel_id
    assert persisted_record.floor_number == -2


def test_api_persist_ulpin_duplicate_conflict(cadastral_hierarchy):
    """
    Test POST /api/v1/ulpin/generate returns HTTP 409 Conflict when
    attempting to persist duplicate records.
    """
    hierarchy = cadastral_hierarchy
    parcel = hierarchy["parcel"]

    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": parcel.parcel_id,
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
        "persist": True,
    }

    # Initial creation -> 201
    r1 = client.post("/api/v1/ulpin/generate", json=payload)
    assert r1.status_code == 201

    # Duplicate creation -> 409
    r2 = client.post("/api/v1/ulpin/generate", json=payload)
    assert r2.status_code == 409
    data = r2.json()
    assert data["success"] is False
    assert "already exists" in data["error"] or "already has assigned" in data["error"]


def test_api_persist_ulpin_direct_unit_id(db: Session, cadastral_hierarchy):
    """
    Test POST /api/v1/ulpin/generate supplying explicit unit_id.
    """
    hierarchy = cadastral_hierarchy
    parcel = hierarchy["parcel"]
    unit_apt = hierarchy["unit_apartment"]

    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": parcel.parcel_id,
        "building": "B001",
        "floor": "F04",
        "unit": "U402",
        "type": "RES",
        "unit_id": str(unit_apt.id),
    }

    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["persisted"] is True
    assert data["unit_id"] == str(unit_apt.id)

    # Database verification
    db_rec = db.query(ULPIN3D).filter(ULPIN3D.unit_id == unit_apt.id).first()
    assert db_rec is not None
    assert db_rec.floor_number == 4


def test_api_persist_unit_not_found():
    """
    Test POST /api/v1/ulpin/generate returns HTTP 404 when unit cannot be resolved.
    """
    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": "NOTFOUND99",
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
        "persist": True,
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "Referenced unit not found" in data["error"]


def test_api_persist_invalid_input():
    """
    Test POST /api/v1/ulpin/generate returns HTTP 400 when input validation fails.
    """
    payload = {
        "state": "INVALID_STATE",
        "district": "NOI",
        "parcel": "55443322",
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
        "persist": True,
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "State must contain exactly 2 uppercase alphabetic characters" in data["error"]
