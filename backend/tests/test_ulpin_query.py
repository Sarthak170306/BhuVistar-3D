import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.building import Building
from app.models.floor import Floor
from app.models.owner import Owner
from app.models.ownership_right import OwnershipRight
from app.models.parcel import Parcel
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit
from app.services.ulpin_record_service import (
    create_ulpin_record,
    get_ulpin_record_by_code,
    get_ulpin_record_by_unit_id,
    get_ulpin_records_by_parcel,
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
def query_cadastral_setup(db: Session):
    """
    Creates an authoritative test dataset:
    - 1 Parcel with parcel_id e.g. 'PRCLQRY101'
    - 1 Building 'B001'
    - 3 Floors: -1 (B01), 1 (F01), 2 (F02)
    - 3 Units: UP01 (PRK), U101 (RES), U201 (COM)
    - 3 Persisted ULPIN3D records
    - 1 Owner with sensitive PII linked to Unit U101 via OwnershipRight
    Cleans up all entities after test completion.
    """
    parcel_ref = f"QRY{uuid.uuid4().hex[:8].upper()}"

    parcel = Parcel(
        parcel_id=parcel_ref,
        state="UP",
        district="NOI",
        address="Commercial Complex Sector 18",
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B003",
        parcel_id=parcel.id,
        name="Plaza One",
    )
    db.add(building)
    db.flush()

    floor_b1 = Floor(building_id=building.id, floor_number=-1, floor_name="Basement 1")
    floor_f1 = Floor(building_id=building.id, floor_number=1, floor_name="First Floor")
    floor_f2 = Floor(building_id=building.id, floor_number=2, floor_name="Second Floor")
    db.add_all([floor_b1, floor_f1, floor_f2])
    db.flush()

    unit_prk = Unit(building_id=building.id, floor_id=floor_b1.id, unit_code="UP01", unit_type="PRK")
    unit_res = Unit(building_id=building.id, floor_id=floor_f1.id, unit_code="U101", unit_type="RES")
    unit_com = Unit(building_id=building.id, floor_id=floor_f2.id, unit_code="U201", unit_type="COM")
    db.add_all([unit_prk, unit_res, unit_com])
    db.flush()

    # Create Owner with PII to verify it is NEVER exposed through retrieval endpoints
    owner = Owner(
        owner_reference=f"OWN_{uuid.uuid4().hex[:6]}",
        name="Rajesh Kumar Sharma",
        contact_reference="rajesh.sharma@example.com / +919876543210",
    )
    db.add(owner)
    db.flush()

    right = OwnershipRight(
        unit_id=unit_res.id,
        owner_id=owner.id,
        ownership_percentage=100.0,
        right_type="FREEHOLD",
    )
    db.add(right)
    db.flush()

    # Create 3 ULPIN records
    ulpin1, rec1 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B003",
        floor="B01",
        unit="UP01",
        property_type="PRK",
        unit_id=unit_prk.id,
    )
    ulpin2, rec2 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B003",
        floor="F01",
        unit="U101",
        property_type="RES",
        unit_id=unit_res.id,
    )
    ulpin3, rec3 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B003",
        floor="F02",
        unit="U201",
        property_type="COM",
        unit_id=unit_com.id,
    )

    yield {
        "parcel": parcel,
        "building": building,
        "units": [unit_prk, unit_res, unit_com],
        "ulpins": [ulpin1, ulpin2, ulpin3],
        "records": [rec1, rec2, rec3],
        "owner": owner,
        "right": right,
    }

    # Teardown
    db.query(OwnershipRight).filter(OwnershipRight.id == right.id).delete()
    db.query(Owner).filter(Owner.id == owner.id).delete()
    db.query(ULPIN3D).filter(ULPIN3D.parcel_id_reference == parcel_ref).delete()
    db.query(Unit).filter(Unit.id.in_([unit_prk.id, unit_res.id, unit_com.id])).delete()
    db.query(Floor).filter(Floor.id.in_([floor_b1.id, floor_f1.id, floor_f2.id])).delete()
    db.query(Building).filter(Building.id == building.id).delete()
    db.query(Parcel).filter(Parcel.id == parcel.id).delete()
    db.commit()


def test_get_ulpin_by_code_success(query_cadastral_setup):
    """1. Test GET /api/v1/ulpin/{ulpin_3d} returns HTTP 200 with cadastral data."""
    setup = query_cadastral_setup
    target_ulpin = setup["ulpins"][1]  # U101 RES
    unit_res = setup["units"][1]

    response = client.get(f"/api/v1/ulpin/{target_ulpin}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "data" in res_data

    item = res_data["data"]
    assert item["ulpin_3d"] == target_ulpin
    assert item["unit_id"] == str(unit_res.id)
    assert item["parcel_id_reference"] == setup["parcel"].parcel_id
    assert item["building_id_reference"] == "B003"
    assert item["floor_number"] == 1
    assert item["unit_code"] == "U101"
    assert item["unit_type"] == "RES"
    assert item["generation_version"] == "1.0"
    assert "created_at" in item


def test_get_ulpin_by_code_not_found():
    """2. Test GET /api/v1/ulpin/{ulpin_3d} returns HTTP 404 for non-existent ULPIN."""
    dummy_ulpin = "BV3D-UP-NOI-NONEXIST99-B003-F01-U101-RES"
    response = client.get(f"/api/v1/ulpin/{dummy_ulpin}")
    assert response.status_code == 404
    res_data = response.json()
    assert res_data["success"] is False
    assert "not found" in res_data["error"].lower()
    assert "detail" in res_data


def test_get_ulpin_by_unit_id_success(query_cadastral_setup):
    """3. Test GET /api/v1/ulpin/unit/{unit_id} returns HTTP 200 when unit has a ULPIN."""
    setup = query_cadastral_setup
    unit_prk = setup["units"][0]
    expected_ulpin = setup["ulpins"][0]

    response = client.get(f"/api/v1/ulpin/unit/{unit_prk.id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["ulpin_3d"] == expected_ulpin
    assert res_data["data"]["unit_id"] == str(unit_prk.id)
    assert res_data["data"]["floor_number"] == -1
    assert res_data["data"]["unit_type"] == "PRK"


def test_get_ulpin_by_unit_id_not_found():
    """4. Test GET /api/v1/ulpin/unit/{unit_id} returns HTTP 404 when unit has no ULPIN record."""
    random_uuid = uuid.uuid4()
    response = client.get(f"/api/v1/ulpin/unit/{random_uuid}")
    assert response.status_code == 404
    res_data = response.json()
    assert res_data["success"] is False
    assert "not found" in res_data["error"].lower()


def test_get_ulpin_by_unit_id_invalid_uuid():
    """5. Test GET /api/v1/ulpin/unit/{unit_id} returns HTTP 422 on invalid UUID format."""
    response = client.get("/api/v1/ulpin/unit/invalid-uuid-12345")
    assert response.status_code == 422


def test_get_ulpins_by_parcel_multiple_records(query_cadastral_setup):
    """6. Test GET /api/v1/ulpin/parcel/{parcel_id} returns deterministic collection."""
    setup = query_cadastral_setup
    parcel_ref = setup["parcel"].parcel_id

    response = client.get(f"/api/v1/ulpin/parcel/{parcel_ref}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["count"] == 3
    assert len(res_data["data"]) == 3

    # Verify deterministic ordering by floor_number: -1 (B01), 1 (F01), 2 (F02)
    floors = [item["floor_number"] for item in res_data["data"]]
    assert floors == [-1, 1, 2]

    # Verify all records reference the correct parcel
    for item in res_data["data"]:
        assert item["parcel_id_reference"] == parcel_ref
        assert item["building_id_reference"] == "B003"


def test_get_ulpins_by_parcel_empty_result():
    """7. Test GET /api/v1/ulpin/parcel/{parcel_id} returns HTTP 200 with empty list."""
    response = client.get("/api/v1/ulpin/parcel/EMPTY_PARCEL_999")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["count"] == 0
    assert res_data["data"] == []


def test_response_schema_validation(query_cadastral_setup):
    """8. Test response schema conformity and field type validations."""
    setup = query_cadastral_setup
    target_ulpin = setup["ulpins"][2]  # U201 COM

    response = client.get(f"/api/v1/ulpin/{target_ulpin}")
    assert response.status_code == 200
    data = response.json()["data"]

    # Validate essential schema fields
    required_keys = [
        "record_id",
        "ulpin_3d",
        "unit_id",
        "parcel_id_reference",
        "building_id_reference",
        "floor_number",
        "unit_code",
        "unit_type",
        "generation_version",
        "created_at",
    ]
    for key in required_keys:
        assert key in data
        assert data[key] is not None


def test_owner_pii_not_exposed(query_cadastral_setup):
    """9. Test that Owner PII is strictly excluded from all retrieval responses."""
    setup = query_cadastral_setup
    target_ulpin = setup["ulpins"][1]  # linked to owner
    unit_res = setup["units"][1]
    parcel_ref = setup["parcel"].parcel_id

    # Check GET by ULPIN
    r1 = client.get(f"/api/v1/ulpin/{target_ulpin}").text.lower()
    # Check GET by Unit
    r2 = client.get(f"/api/v1/ulpin/unit/{unit_res.id}").text.lower()
    # Check GET by Parcel
    r3 = client.get(f"/api/v1/ulpin/parcel/{parcel_ref}").text.lower()

    forbidden_pii_terms = [
        "rajesh",
        "sharma",
        "abcde1234f",  # PAN
        "99887766",    # Aadhaar hash snippet
        "+919876543210",
        "rajesh.sharma@example.com",
    ]

    for body in [r1, r2, r3]:
        for pii in forbidden_pii_terms:
            assert pii.lower() not in body, f"PII leak detected: {pii}"


def test_service_layer_queries_direct(db: Session, query_cadastral_setup):
    """10. Test direct service layer queries."""
    setup = query_cadastral_setup
    ulpin_code = setup["ulpins"][0]
    unit_prk = setup["units"][0]
    parcel_ref = setup["parcel"].parcel_id

    # Test get_ulpin_record_by_code
    rec = get_ulpin_record_by_code(db, ulpin_code)
    assert rec is not None
    assert rec.ulpin_3d == ulpin_code

    # Test get_ulpin_record_by_unit_id
    rec_by_unit = get_ulpin_record_by_unit_id(db, unit_prk.id)
    assert rec_by_unit is not None
    assert rec_by_unit.unit_id == unit_prk.id

    # Test get_ulpin_records_by_parcel
    records = get_ulpin_records_by_parcel(db, parcel_ref)
    assert len(records) == 3
    assert [r.floor_number for r in records] == [-1, 1, 2]

    # Non-existent queries
    assert get_ulpin_record_by_code(db, "NONEXISTENT") is None
    assert get_ulpin_record_by_unit_id(db, uuid.uuid4()) is None
    assert get_ulpin_records_by_parcel(db, "EMPTY_PARCEL") == []
