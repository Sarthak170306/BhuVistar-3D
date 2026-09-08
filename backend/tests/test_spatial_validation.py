import uuid
import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.building import Building
from app.models.floor import Floor
from app.models.owner import Owner
from app.models.ownership_right import OwnershipRight
from app.models.parcel import Parcel
from app.models.unit import Unit
from app.schemas.spatial import UnitSpatialValidationResponse
from app.services.spatial_validation_service import (
    InvalidGeometryError,
    SpatialContainmentError,
    SpatialValidationError,
    validate_building_geometry,
    validate_building_within_parcel,
    validate_floor_geometry,
    validate_parcel_geometry,
    validate_unit_geometry,
    validate_unit_spatial_hierarchy,
    validate_unit_within_parent,
)

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture with guaranteed cleanup."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def spatial_cadastral_setup(db: Session):
    """
    Creates an authoritative spatial cadastral hierarchy:
    - Parcel: [77.30, 28.50] to [77.40, 28.60]
    - Building: [77.32, 28.52] to [77.38, 28.58] (contained in parcel)
    - Floor 1: [77.33, 28.53] to [77.37, 28.57] (contained in building)
    - Unit 1: 3D geometry [77.34, 28.54] to [77.36, 28.56], Z=10.0m (contained in Floor 1)
    - Floor 2: None geometry (optional elevation datum)
    - Unit 2: 3D geometry [77.34, 28.54] to [77.36, 28.56], Z=20.0m (contained in Building directly)
    - Owner + OwnershipRight with sensitive PII
    """
    parcel_ref = f"SPAT_{uuid.uuid4().hex[:8].upper()}"

    parcel = Parcel(
        parcel_id=parcel_ref,
        state="UP",
        district="NOI",
        address="Sector 62 Spatial Verification Hub",
        geometry=WKTElement(
            "POLYGON ((77.30 28.50, 77.30 28.60, 77.40 28.60, 77.40 28.50, 77.30 28.50))",
            srid=4326,
        ),
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B001",
        parcel_id=parcel.id,
        name="Paramount 3D Tower",
        geometry=WKTElement(
            "POLYGON ((77.32 28.52, 77.32 28.58, 77.38 28.58, 77.38 28.52, 77.32 28.52))",
            srid=4326,
        ),
    )
    db.add(building)
    db.flush()

    # Floor with 2D geometry
    floor_f1 = Floor(
        building_id=building.id,
        floor_number=1,
        floor_name="First Floor",
        elevation_m=10.0,
        height_m=3.5,
        geometry=WKTElement(
            "POLYGON ((77.33 28.53, 77.33 28.57, 77.37 28.57, 77.37 28.53, 77.33 28.53))",
            srid=4326,
        ),
    )
    # Floor without 2D geometry (optional floor plate)
    floor_f2 = Floor(
        building_id=building.id,
        floor_number=2,
        floor_name="Second Floor",
        elevation_m=20.0,
        height_m=3.5,
        geometry=None,
    )
    db.add_all([floor_f1, floor_f2])
    db.flush()

    # Unit 1 on Floor 1
    unit_1 = Unit(
        building_id=building.id,
        floor_id=floor_f1.id,
        unit_code="U101",
        unit_type="RES",
        geometry=WKTElement(
            "POLYGON Z ((77.34 28.54 10.0, 77.34 28.56 10.0, 77.36 28.56 10.0, 77.36 28.54 10.0, 77.34 28.54 10.0))",
            srid=4326,
        ),
    )
    # Unit 2 on Floor 2 (floor has no geometry, unit contained within building)
    unit_2 = Unit(
        building_id=building.id,
        floor_id=floor_f2.id,
        unit_code="U201",
        unit_type="COM",
        geometry=WKTElement(
            "POLYGON Z ((77.34 28.54 20.0, 77.34 28.56 20.0, 77.36 28.56 20.0, 77.36 28.54 20.0, 77.34 28.54 20.0))",
            srid=4326,
        ),
    )
    db.add_all([unit_1, unit_2])
    db.flush()

    # Owner with confidential PII
    owner = Owner(
        owner_reference=f"OWN_{uuid.uuid4().hex[:6]}",
        name="Devendra Pratap Singh",
        contact_reference="devendra.singh@cadastre.in / +919811223344",
    )
    db.add(owner)
    db.flush()

    right = OwnershipRight(
        unit_id=unit_1.id,
        owner_id=owner.id,
        ownership_percentage=100.0,
        right_type="FREEHOLD",
    )
    db.add(right)
    db.commit()

    yield {
        "parcel": parcel,
        "building": building,
        "floor_1": floor_f1,
        "floor_2": floor_f2,
        "unit_1": unit_1,
        "unit_2": unit_2,
        "owner": owner,
        "right": right,
    }

    # Teardown
    db.query(OwnershipRight).filter(OwnershipRight.id == right.id).delete()
    db.query(Owner).filter(Owner.id == owner.id).delete()
    db.query(Unit).filter(Unit.id.in_([unit_1.id, unit_2.id])).delete()
    db.query(Floor).filter(Floor.id.in_([floor_f1.id, floor_f2.id])).delete()
    db.query(Building).filter(Building.id == building.id).delete()
    db.query(Parcel).filter(Parcel.id == parcel.id).delete()
    db.commit()


def test_valid_hierarchy_with_floor_geometry(spatial_cadastral_setup):
    """1. Test valid parcel/building/floor/unit hierarchy returns HTTP 200 with all checks True."""
    setup = spatial_cadastral_setup
    unit_id = setup["unit_1"].id

    response = client.post(f"/api/v1/spatial/validate-unit/{unit_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["valid"] is True
    assert data["unit_id"] == str(unit_id)
    assert data["checks"]["unit_geometry_valid"] is True
    assert data["checks"]["floor_geometry_valid"] is True
    assert data["checks"]["building_geometry_valid"] is True
    assert data["checks"]["building_within_parcel"] is True
    assert data["checks"]["unit_within_parent"] is True


def test_valid_hierarchy_without_floor_geometry(spatial_cadastral_setup):
    """1b. Test valid hierarchy when floor geometry is omitted (unit validated directly within building)."""
    setup = spatial_cadastral_setup
    unit_id = setup["unit_2"].id

    response = client.post(f"/api/v1/spatial/validate-unit/{unit_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["valid"] is True
    assert data["checks"]["unit_geometry_valid"] is True
    assert data["checks"]["floor_geometry_valid"] is True
    assert data["checks"]["building_geometry_valid"] is True
    assert data["checks"]["building_within_parcel"] is True
    assert data["checks"]["unit_within_parent"] is True


def test_invalid_building_geometry(db: Session):
    """2. Test invalid building geometry (self-intersecting polygon) returns HTTP 400."""
    parcel = Parcel(
        parcel_id=f"PAR_{uuid.uuid4().hex[:8]}",
        state="UP",
        district="NOI",
        geometry=WKTElement("POLYGON ((0 0, 0 20, 20 20, 20 0, 0 0))", srid=4326),
    )
    db.add(parcel)
    db.flush()

    # Self-intersecting building polygon (bow-tie)
    bad_building = Building(
        building_id="B_BAD_GEOM",
        parcel_id=parcel.id,
        name="Invalid Building Tower",
        geometry=WKTElement("POLYGON ((2 2, 2 8, 8 2, 8 8, 2 2))", srid=4326),
    )
    db.add(bad_building)
    db.flush()

    floor = Floor(building_id=bad_building.id, floor_number=1, floor_name="1F")
    db.add(floor)
    db.flush()

    unit = Unit(
        building_id=bad_building.id,
        floor_id=floor.id,
        unit_code="U01",
        geometry=WKTElement("POLYGON Z ((3 3 10, 3 5 10, 5 5 10, 5 3 10, 3 3 10))", srid=4326),
    )
    db.add(unit)
    db.commit()

    try:
        response = client.post(f"/api/v1/spatial/validate-unit/{unit.id}")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["valid"] is False
        assert data["checks"]["building_geometry_valid"] is False
        assert "invalid" in data["error"].lower() or "self-intersection" in data["error"].lower()
    finally:
        db.query(Unit).filter(Unit.id == unit.id).delete()
        db.query(Floor).filter(Floor.id == floor.id).delete()
        db.query(Building).filter(Building.id == bad_building.id).delete()
        db.query(Parcel).filter(Parcel.id == parcel.id).delete()
        db.commit()


def test_building_outside_parcel(db: Session):
    """3. Test building footprint outside parent parcel boundary returns HTTP 400."""
    parcel = Parcel(
        parcel_id=f"PAR_{uuid.uuid4().hex[:8]}",
        state="UP",
        district="NOI",
        geometry=WKTElement("POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", srid=4326),
    )
    db.add(parcel)
    db.flush()

    # Building entirely outside parcel (located at 20..30)
    outside_building = Building(
        building_id="B_OUTSIDE",
        parcel_id=parcel.id,
        name="Outside Tower",
        geometry=WKTElement("POLYGON ((20 20, 20 25, 25 25, 25 20, 20 20))", srid=4326),
    )
    db.add(outside_building)
    db.flush()

    floor = Floor(building_id=outside_building.id, floor_number=1, floor_name="1F")
    db.add(floor)
    db.flush()

    unit = Unit(
        building_id=outside_building.id,
        floor_id=floor.id,
        unit_code="U01",
        geometry=WKTElement("POLYGON Z ((21 21 5, 21 23 5, 23 23 5, 23 21 5, 21 21 5))", srid=4326),
    )
    db.add(unit)
    db.commit()

    try:
        response = client.post(f"/api/v1/spatial/validate-unit/{unit.id}")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["valid"] is False
        assert data["checks"]["building_within_parcel"] is False
        assert "not spatially contained" in data["error"].lower() or "outside" in data["error"].lower()
    finally:
        db.query(Unit).filter(Unit.id == unit.id).delete()
        db.query(Floor).filter(Floor.id == floor.id).delete()
        db.query(Building).filter(Building.id == outside_building.id).delete()
        db.query(Parcel).filter(Parcel.id == parcel.id).delete()
        db.commit()


def test_invalid_floor_geometry(db: Session):
    """4. Test invalid floor geometry (self-intersecting) returns HTTP 400."""
    parcel = Parcel(
        parcel_id=f"PAR_{uuid.uuid4().hex[:8]}",
        state="UP",
        district="NOI",
        geometry=WKTElement("POLYGON ((0 0, 0 30, 30 30, 30 0, 0 0))", srid=4326),
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B_VALID",
        parcel_id=parcel.id,
        name="Valid Tower",
        geometry=WKTElement("POLYGON ((5 5, 5 25, 25 25, 25 5, 5 5))", srid=4326),
    )
    db.add(building)
    db.flush()

    # Self-intersecting floor polygon
    bad_floor = Floor(
        building_id=building.id,
        floor_number=1,
        floor_name="Bad Floor",
        geometry=WKTElement("POLYGON ((6 6, 6 12, 12 6, 12 12, 6 6))", srid=4326),
    )
    db.add(bad_floor)
    db.flush()

    unit = Unit(
        building_id=building.id,
        floor_id=bad_floor.id,
        unit_code="U01",
        geometry=WKTElement("POLYGON Z ((7 7 5, 7 8 5, 8 8 5, 8 7 5, 7 7 5))", srid=4326),
    )
    db.add(unit)
    db.commit()

    try:
        response = client.post(f"/api/v1/spatial/validate-unit/{unit.id}")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["valid"] is False
        assert data["checks"]["floor_geometry_valid"] is False
    finally:
        db.query(Unit).filter(Unit.id == unit.id).delete()
        db.query(Floor).filter(Floor.id == bad_floor.id).delete()
        db.query(Building).filter(Building.id == building.id).delete()
        db.query(Parcel).filter(Parcel.id == parcel.id).delete()
        db.commit()


def test_unit_outside_parent_geometry(db: Session):
    """5. Test unit geometry outside parent floor/building geometry returns HTTP 400."""
    parcel = Parcel(
        parcel_id=f"PAR_{uuid.uuid4().hex[:8]}",
        state="UP",
        district="NOI",
        geometry=WKTElement("POLYGON ((0 0, 0 30, 30 30, 30 0, 0 0))", srid=4326),
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B_VALID_2",
        parcel_id=parcel.id,
        name="Tower B",
        geometry=WKTElement("POLYGON ((5 5, 5 15, 15 15, 15 5, 5 5))", srid=4326),
    )
    db.add(building)
    db.flush()

    floor = Floor(
        building_id=building.id,
        floor_number=1,
        floor_name="1F",
        geometry=WKTElement("POLYGON ((6 6, 6 14, 14 14, 14 6, 6 6))", srid=4326),
    )
    db.add(floor)
    db.flush()

    # Unit geometry located at [20, 20], far outside building and floor [5..15]
    outside_unit = Unit(
        building_id=building.id,
        floor_id=floor.id,
        unit_code="U_OUTSIDE",
        geometry=WKTElement("POLYGON Z ((20 20 5, 20 22 5, 22 22 5, 22 20 5, 20 20 5))", srid=4326),
    )
    db.add(outside_unit)
    db.commit()

    try:
        response = client.post(f"/api/v1/spatial/validate-unit/{outside_unit.id}")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["valid"] is False
        assert data["checks"]["unit_within_parent"] is False
        assert "not spatially contained" in data["error"].lower()
    finally:
        db.query(Unit).filter(Unit.id == outside_unit.id).delete()
        db.query(Floor).filter(Floor.id == floor.id).delete()
        db.query(Building).filter(Building.id == building.id).delete()
        db.query(Parcel).filter(Parcel.id == parcel.id).delete()
        db.commit()


def test_missing_geometry(db: Session):
    """6. Test safe handling when unit geometry is missing/null returns HTTP 400 without crashing."""
    parcel = Parcel(
        parcel_id=f"PAR_{uuid.uuid4().hex[:8]}",
        state="UP",
        district="NOI",
        geometry=WKTElement("POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", srid=4326),
    )
    db.add(parcel)
    db.flush()

    building = Building(
        building_id="B_NULL_GEOM",
        parcel_id=parcel.id,
        name="Tower Null",
        geometry=WKTElement("POLYGON ((2 2, 2 8, 8 8, 8 2, 2 2))", srid=4326),
    )
    db.add(building)
    db.flush()

    floor = Floor(building_id=building.id, floor_number=1, floor_name="1F")
    db.add(floor)
    db.flush()

    # Unit with missing (None) geometry
    null_unit = Unit(
        building_id=building.id,
        floor_id=floor.id,
        unit_code="U_NOGEOM",
        geometry=None,
    )
    db.add(null_unit)
    db.commit()

    try:
        response = client.post(f"/api/v1/spatial/validate-unit/{null_unit.id}")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["valid"] is False
        assert data["checks"]["unit_geometry_valid"] is False
        assert "missing or null" in data["error"].lower()
    finally:
        db.query(Unit).filter(Unit.id == null_unit.id).delete()
        db.query(Floor).filter(Floor.id == floor.id).delete()
        db.query(Building).filter(Building.id == building.id).delete()
        db.query(Parcel).filter(Parcel.id == parcel.id).delete()
        db.commit()


def test_invalid_unit_uuid():
    """7. Test invalid unit UUID format returns HTTP 400."""
    response = client.post("/api/v1/spatial/validate-unit/not-a-valid-uuid-12345")
    assert response.status_code in (400, 422)
    data = response.json()
    assert data["success"] is False or "detail" in data


def test_missing_unit():
    """8. Test non-existent unit UUID returns HTTP 404."""
    random_id = uuid.uuid4()
    response = client.post(f"/api/v1/spatial/validate-unit/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_successful_api_response_schema(spatial_cadastral_setup):
    """9. Test that successful API response validates strictly against UnitSpatialValidationResponse schema."""
    setup = spatial_cadastral_setup
    unit_id = setup["unit_1"].id

    response = client.post(f"/api/v1/spatial/validate-unit/{unit_id}")
    assert response.status_code == 200
    data = response.json()

    # Pydantic schema validation
    validated = UnitSpatialValidationResponse(**data)
    assert validated.success is True
    assert validated.valid is True
    assert validated.unit_id == str(unit_id)
    assert validated.checks.unit_geometry_valid is True
    assert validated.checks.floor_geometry_valid is True
    assert validated.checks.building_geometry_valid is True
    assert validated.checks.building_within_parcel is True
    assert validated.checks.unit_within_parent is True


def test_owner_pii_not_exposed(spatial_cadastral_setup):
    """10. Test that Owner PII is never exposed through the spatial validation API."""
    setup = spatial_cadastral_setup
    unit_id = setup["unit_1"].id

    response = client.post(f"/api/v1/spatial/validate-unit/{unit_id}")
    assert response.status_code == 200
    body = response.text.lower()

    forbidden_pii = [
        "devendra",
        "singh",
        "cadastre.in",
        "+919811223344",
        "freehold",
    ]
    for term in forbidden_pii:
        assert term not in body, f"Owner PII leak detected: '{term}'"


def test_service_layer_direct_validation(db: Session, spatial_cadastral_setup):
    """11. Test direct service layer functions for individual entities and containment."""
    setup = spatial_cadastral_setup
    parcel = setup["parcel"]
    building = setup["building"]
    floor = setup["floor_1"]
    unit = setup["unit_1"]

    # Test single-entity validators
    assert validate_parcel_geometry(db, parcel) is True
    assert validate_building_geometry(db, building) is True
    assert validate_floor_geometry(db, floor) is True
    assert validate_unit_geometry(db, unit) is True

    # Test containment validators
    assert validate_building_within_parcel(db, building, parcel) is True
    assert validate_unit_within_parent(db, unit, floor, building) is True

    # Test hierarchy service directly
    res = validate_unit_spatial_hierarchy(db, unit.id, raise_on_error=False)
    assert res["valid"] is True
    assert res["errors"] == []

    # Test raise_on_error=True on invalid geometry
    bad_geom = WKTElement("POLYGON ((0 0, 0 2, 2 0, 2 2, 0 0))", srid=4326)
    bad_building = Building(
        building_id="B_TEST_SVC",
        parcel_id=parcel.id,
        name="Bad Svc Bldg",
        geometry=bad_geom,
    )
    with pytest.raises(InvalidGeometryError):
        validate_building_geometry(db, bad_building, raise_on_error=True)


def test_existing_apis_unaffected():
    """12. Test that existing health, ULPIN generation, and retrieval endpoints continue functioning."""
    # Health checks
    r_health = client.get("/health")
    assert r_health.status_code == 200

    r_db = client.get("/health/db")
    assert r_db.status_code == 200
    assert r_db.json()["database"] == "connected"

    # Pure ULPIN generation without persistence
    payload = {
        "state": "DL",
        "district": "NDL",
        "parcel": "11223344",
        "building": "B01",
        "floor": "F01",
        "unit": "U01",
        "type": "RES",
        "persist": False,
    }
    r_gen = client.post("/api/v1/ulpin/generate", json=payload)
    assert r_gen.status_code == 200
    assert r_gen.json()["success"] is True
