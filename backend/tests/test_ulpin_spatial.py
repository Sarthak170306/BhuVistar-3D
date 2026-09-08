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
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit
from app.services.ulpin_record_service import create_ulpin_record
from app.services.ulpin_spatial_service import (
    SpatialValidationError,
    find_ulpins_at_point,
    find_ulpins_by_height_range,
    find_ulpins_intersecting_geometry,
    find_ulpins_within_bbox,
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
    Creates an authoritative 3D spatial cadastral hierarchy:
    - 1 Parcel around lon [77.30, 77.40], lat [28.50, 28.60]
    - 1 Building around lon [77.32, 77.38], lat [28.52, 28.58]
    - 3 Floors with elevations:
      - Basement 1 (elevation -3.0m, height 3.0m)
      - 1st Floor (elevation 10.0m, height 3.5m)
      - 5th Floor (elevation 25.0m, height 3.5m)
    - 3 Units with 3D geometries (GEOMETRYZ with Z coords):
      - Unit UP01 (PRK) at Z=-3.0m
      - Unit U101 (RES) at Z=10.0m
      - Unit U501 (OFF) at Z=25.0m
    - 3 Persisted 3D ULPIN records
    - 1 Owner with PII to verify it is never exposed in spatial APIs.
    """
    parcel_ref = f"SPAT{uuid.uuid4().hex[:8].upper()}"

    parcel = Parcel(
        parcel_id=parcel_ref,
        state="UP",
        district="NOI",
        address="Sector 62 Spatial Innovation Park",
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
        name="Apex 3D Tower",
        geometry=WKTElement(
            "POLYGON ((77.32 28.52, 77.32 28.58, 77.38 28.58, 77.38 28.52, 77.32 28.52))",
            srid=4326,
        ),
    )
    db.add(building)
    db.flush()

    floor_b1 = Floor(building_id=building.id, floor_number=-1, floor_name="Basement Level 1", elevation_m=-3.0, height_m=3.0)
    floor_f1 = Floor(building_id=building.id, floor_number=1, floor_name="Floor 1", elevation_m=10.0, height_m=3.5)
    floor_f5 = Floor(building_id=building.id, floor_number=5, floor_name="Floor 5", elevation_m=25.0, height_m=3.5)
    db.add_all([floor_b1, floor_f1, floor_f5])
    db.flush()

    # 3D geometries with Z coordinates in EPSG:4326
    unit_prk = Unit(
        building_id=building.id,
        floor_id=floor_b1.id,
        unit_code="UP01",
        unit_type="PRK",
        geometry=WKTElement(
            "POLYGON Z ((77.33 28.53 -3.0, 77.33 28.57 -3.0, 77.37 28.57 -3.0, 77.37 28.53 -3.0, 77.33 28.53 -3.0))",
            srid=4326,
        ),
    )
    unit_res = Unit(
        building_id=building.id,
        floor_id=floor_f1.id,
        unit_code="U101",
        unit_type="RES",
        geometry=WKTElement(
            "POLYGON Z ((77.34 28.54 10.0, 77.34 28.56 10.0, 77.36 28.56 10.0, 77.36 28.54 10.0, 77.34 28.54 10.0))",
            srid=4326,
        ),
    )
    unit_off = Unit(
        building_id=building.id,
        floor_id=floor_f5.id,
        unit_code="U501",
        unit_type="OFF",
        geometry=WKTElement(
            "POLYGON Z ((77.34 28.54 25.0, 77.34 28.56 25.0, 77.36 28.56 25.0, 77.36 28.54 25.0, 77.34 28.54 25.0))",
            srid=4326,
        ),
    )
    db.add_all([unit_prk, unit_res, unit_off])
    db.flush()

    # Sensitive Owner data
    owner = Owner(
        owner_reference=f"OWN_{uuid.uuid4().hex[:6]}",
        name="Vikramaditya Singhania",
        contact_reference="vikram.singhania@example.com / +919999888877",
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

    # Persist ULPIN records
    u1, rec1 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B001",
        floor="B01",
        unit="UP01",
        property_type="PRK",
        unit_id=unit_prk.id,
    )
    u2, rec2 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B001",
        floor="F01",
        unit="U101",
        property_type="RES",
        unit_id=unit_res.id,
    )
    u3, rec3 = create_ulpin_record(
        db,
        state="UP",
        district="NOI",
        parcel=parcel_ref,
        building="B001",
        floor="F05",
        unit="U501",
        property_type="OFF",
        unit_id=unit_off.id,
    )

    yield {
        "parcel": parcel,
        "building": building,
        "units": [unit_prk, unit_res, unit_off],
        "ulpins": [u1, u2, u3],
        "records": [rec1, rec2, rec3],
        "owner": owner,
        "right": right,
    }

    # Teardown
    db.query(OwnershipRight).filter(OwnershipRight.id == right.id).delete()
    db.query(Owner).filter(Owner.id == owner.id).delete()
    db.query(ULPIN3D).filter(ULPIN3D.parcel_id_reference == parcel_ref).delete()
    db.query(Unit).filter(Unit.id.in_([unit_prk.id, unit_res.id, unit_off.id])).delete()
    db.query(Floor).filter(Floor.id.in_([floor_b1.id, floor_f1.id, floor_f5.id])).delete()
    db.query(Building).filter(Building.id == building.id).delete()
    db.query(Parcel).filter(Parcel.id == parcel.id).delete()
    db.commit()


def test_bbox_query_matching_records(spatial_cadastral_setup):
    """1. Test GET /api/v1/ulpin/spatial/bbox returns matching records."""
    response = client.get(
        "/api/v1/ulpin/spatial/bbox?min_lon=77.32&min_lat=28.52&max_lon=77.38&max_lat=28.58"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 3
    assert len(data["data"]) == 3

    # Check that all returned records have valid fields
    for item in data["data"]:
        assert item["parcel_id_reference"] == spatial_cadastral_setup["parcel"].parcel_id
        assert item["ulpin_3d"].startswith("BV3D-UP-NOI-")


def test_bbox_query_empty_collection():
    """2. Test GET /api/v1/ulpin/spatial/bbox returns empty collection when no match."""
    response = client.get(
        "/api/v1/ulpin/spatial/bbox?min_lon=78.0&min_lat=29.0&max_lon=78.1&max_lat=29.1"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 0
    assert data["data"] == []


def test_point_query_matching_record(spatial_cadastral_setup):
    """3. Test GET /api/v1/ulpin/spatial/point returns intersecting 3D ULPIN records."""
    # Point located at 77.35, 28.55 (intersects all 3 units' vertical footprint)
    response = client.get(
        "/api/v1/ulpin/spatial/point?longitude=77.35&latitude=28.55"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 3

    ulpins = [r["ulpin_3d"] for r in data["data"]]
    for expected in spatial_cadastral_setup["ulpins"]:
        assert expected in ulpins


def test_point_query_no_records():
    """4. Test GET /api/v1/ulpin/spatial/point returns empty collection when point is outside."""
    response = client.get(
        "/api/v1/ulpin/spatial/point?longitude=79.0&latitude=29.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 0
    assert data["data"] == []


def test_invalid_longitude():
    """5. Test HTTP 422 when longitude exceeds valid range [-180, 180]."""
    response = client.get(
        "/api/v1/ulpin/spatial/point?longitude=250.0&latitude=28.5"
    )
    assert response.status_code == 422


def test_invalid_latitude():
    """6. Test HTTP 422 when latitude exceeds valid range [-90, 90]."""
    response = client.get(
        "/api/v1/ulpin/spatial/point?longitude=77.35&latitude=105.0"
    )
    assert response.status_code == 422


def test_invalid_bbox_ordering():
    """7. Test HTTP 422 when bbox bounds are inverted (min > max)."""
    # min_lon > max_lon
    r1 = client.get(
        "/api/v1/ulpin/spatial/bbox?min_lon=78.0&min_lat=28.0&max_lon=77.0&max_lat=29.0"
    )
    assert r1.status_code == 422

    # min_lat > max_lat
    r2 = client.get(
        "/api/v1/ulpin/spatial/bbox?min_lon=77.0&min_lat=29.0&max_lon=78.0&max_lat=28.0"
    )
    assert r2.status_code == 422


def test_z_range_query(spatial_cadastral_setup):
    """8. Test GET /api/v1/ulpin/spatial/z-range for vertical elevation intervals."""
    # 1st Floor (Z=10.0m)
    r1 = client.get("/api/v1/ulpin/spatial/z-range?min_z=8.0&max_z=15.0")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["success"] is True
    assert data1["count"] == 1
    assert data1["data"][0]["unit_code"] == "U101"

    # Basement (Z=-3.0m)
    r2 = client.get("/api/v1/ulpin/spatial/z-range?min_z=-5.0&max_z=0.0")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["success"] is True
    assert data2["count"] == 1
    assert data2["data"][0]["unit_code"] == "UP01"

    # 5th Floor (Z=25.0m)
    r3 = client.get("/api/v1/ulpin/spatial/z-range?min_z=20.0&max_z=30.0")
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["success"] is True
    assert data3["count"] == 1
    assert data3["data"][0]["unit_code"] == "U501"

    # All units span (-5.0m to 30.0m)
    r_all = client.get("/api/v1/ulpin/spatial/z-range?min_z=-10.0&max_z=50.0")
    assert r_all.status_code == 200
    assert r_all.json()["count"] == 3

    # Empty Z range (elevation above building roof)
    r_empty = client.get("/api/v1/ulpin/spatial/z-range?min_z=100.0&max_z=200.0")
    assert r_empty.status_code == 200
    assert r_empty.json()["count"] == 0

    # Invalid Z range (min_z > max_z) -> 422
    r_inv = client.get("/api/v1/ulpin/spatial/z-range?min_z=50.0&max_z=20.0")
    assert r_inv.status_code == 422


def test_response_schema_validation(spatial_cadastral_setup):
    """9. Test response schema structure and typed fields."""
    response = client.get(
        "/api/v1/ulpin/spatial/point?longitude=77.35&latitude=28.55"
    )
    assert response.status_code == 200
    res_json = response.json()
    assert "success" in res_json
    assert "data" in res_json
    assert "count" in res_json

    item = res_json["data"][0]
    expected_fields = [
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
    for field in expected_fields:
        assert field in item
        assert item[field] is not None


def test_owner_pii_not_exposed(spatial_cadastral_setup):
    """10. Test that Owner PII is strictly excluded from all spatial query responses."""
    r_bbox = client.get(
        "/api/v1/ulpin/spatial/bbox?min_lon=77.32&min_lat=28.52&max_lon=77.38&max_lat=28.58"
    ).text.lower()
    r_pt = client.get(
        "/api/v1/ulpin/spatial/point?longitude=77.35&latitude=28.55"
    ).text.lower()
    r_z = client.get(
        "/api/v1/ulpin/spatial/z-range?min_z=8.0&max_z=15.0"
    ).text.lower()

    forbidden = [
        "vikramaditya",
        "singhania",
        "vikram.singhania@example.com",
        "+919999888877",
        "9999888877",
    ]

    for body in [r_bbox, r_pt, r_z]:
        for pii in forbidden:
            assert pii not in body, f"PII leak detected in spatial response: {pii}"


def test_service_layer_spatial_queries(db: Session, spatial_cadastral_setup):
    """11. Direct unit tests for the spatial service layer."""
    # Test find_ulpins_within_bbox
    bbox_res = find_ulpins_within_bbox(
        db,
        min_lon=77.32,
        min_lat=28.52,
        max_lon=77.38,
        max_lat=28.58,
    )
    assert len(bbox_res) == 3

    # Test find_ulpins_at_point
    pt_res = find_ulpins_at_point(
        db,
        longitude=77.35,
        latitude=28.55,
    )
    assert len(pt_res) == 3

    # Test find_ulpins_by_height_range
    z_res = find_ulpins_by_height_range(
        db,
        min_z=8.0,
        max_z=12.0,
    )
    assert len(z_res) == 1
    assert z_res[0].unit_code == "U101"

    # Test find_ulpins_intersecting_geometry with custom polygon
    poly_wkt = "POLYGON ((77.33 28.53, 77.33 28.57, 77.37 28.57, 77.37 28.53, 77.33 28.53))"
    poly_res = find_ulpins_intersecting_geometry(db, geometry_wkt=poly_wkt)
    assert len(poly_res) == 3

    # Validation errors
    with pytest.raises(SpatialValidationError):
        find_ulpins_within_bbox(db, min_lon=78.0, min_lat=28.0, max_lon=77.0, max_lat=29.0)

    with pytest.raises(SpatialValidationError):
        find_ulpins_at_point(db, longitude=200.0, latitude=28.0)

    with pytest.raises(SpatialValidationError):
        find_ulpins_by_height_range(db, min_z=20.0, max_z=10.0)


def test_existing_apis_unaffected(spatial_cadastral_setup):
    """12. Verify that existing endpoints continue to work without regression."""
    # Health check
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "ok"}

    # Database health check
    r_db = client.get("/health/db")
    assert r_db.status_code == 200
    assert r_db.json()["database"] == "connected"

    # GET by ULPIN
    sample_ulpin = spatial_cadastral_setup["ulpins"][0]
    r_ulpin = client.get(f"/api/v1/ulpin/{sample_ulpin}")
    assert r_ulpin.status_code == 200
    assert r_ulpin.json()["data"]["ulpin_3d"] == sample_ulpin
