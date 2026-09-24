import uuid
import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.unit import Unit

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture with guaranteed rollback and cleanup."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def spatial_test_hierarchy(db: Session):
    """
    Creates a full cadastral hierarchy in PostGIS with real 3D geometry:
    - Parcel: 2D polygon in EPSG:4326
    - Building: 2D footprint in EPSG:4326
    - Floor: 2D floor plate with elevation datum
    - Unit 1: 3D geometry with Z coordinates (PolyhedralSurface Z)
    - Unit 2: Unit record without geometry (geometry = None)
    """
    parcel_ref = f"GEOM_{uuid.uuid4().hex[:8].upper()}"
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
        building_id=f"BLD_{uuid.uuid4().hex[:6].upper()}",
        parcel_id=parcel.id,
        name="Authoritative Cadastral Tower",
        total_floors=10,
        height_m=35.0,
        geometry=WKTElement(
            "POLYGON ((77.32 28.52, 77.32 28.58, 77.38 28.58, 77.38 28.52, 77.32 28.52))",
            srid=4326,
        ),
    )
    db.add(building)
    db.flush()

    floor = Floor(
        building_id=building.id,
        floor_number=-2,
        floor_name="Basement Level 2",
        elevation_m=-6.0,
        height_m=3.0,
        geometry=WKTElement(
            "POLYGON ((77.33 28.53, 77.33 28.57, 77.37 28.57, 77.37 28.53, 77.33 28.53))",
            srid=4326,
        ),
    )
    db.add(floor)
    db.flush()

    wkt_polyhedral = """POLYHEDRALSURFACE Z (
        ((77.34 28.54 -5.0, 77.34 28.56 -5.0, 77.36 28.56 -5.0, 77.36 28.54 -5.0, 77.34 28.54 -5.0)),
        ((77.34 28.54 -2.0, 77.36 28.54 -2.0, 77.36 28.56 -2.0, 77.34 28.56 -2.0, 77.34 28.54 -2.0)),
        ((77.34 28.54 -5.0, 77.34 28.54 -2.0, 77.34 28.56 -2.0, 77.34 28.56 -5.0, 77.34 28.54 -5.0)),
        ((77.36 28.54 -5.0, 77.36 28.56 -5.0, 77.36 28.56 -2.0, 77.36 28.54 -2.0, 77.36 28.54 -5.0)),
        ((77.34 28.54 -5.0, 77.36 28.54 -5.0, 77.36 28.54 -2.0, 77.34 28.54 -2.0, 77.34 28.54 -5.0)),
        ((77.34 28.56 -5.0, 77.34 28.56 -2.0, 77.36 28.56 -2.0, 77.36 28.56 -5.0, 77.34 28.56 -5.0))
    )"""

    unit_3d = Unit(
        id=uuid.uuid4(),
        building_id=building.id,
        floor_id=floor.id,
        unit_code="UP32",
        unit_type="Parking Bay",
        usage_type="Vehicle Parking",
        geometry=WKTElement(wkt_polyhedral, srid=4326),
    )
    db.add(unit_3d)

    unit_no_geom = Unit(
        id=uuid.uuid4(),
        building_id=building.id,
        floor_id=floor.id,
        unit_code="UP33",
        unit_type="Storage Unit",
        usage_type="Storage",
        geometry=None,
    )
    db.add(unit_no_geom)
    db.commit()

    yield {
        "parcel": parcel,
        "building": building,
        "floor": floor,
        "unit_3d": unit_3d,
        "unit_no_geom": unit_no_geom,
    }

    # Cleanup
    db.query(Unit).filter(Unit.id.in_([unit_3d.id, unit_no_geom.id])).delete()
    db.query(Floor).filter(Floor.id == floor.id).delete()
    db.query(Building).filter(Building.id == building.id).delete()
    db.query(Parcel).filter(Parcel.id == parcel.id).delete()
    db.commit()


def test_get_unit_geometry_success(spatial_test_hierarchy):
    """Test successful retrieval of authoritative 3D unit geometry."""
    unit_id = str(spatial_test_hierarchy["unit_3d"].id)
    response = client.get(f"/api/v1/spatial/unit/{unit_id}/geometry")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["unit_id"] == unit_id
    assert data["srid"] == 4326
    assert data["has_geometry"] is True
    assert data["geometry_type"] == "PolyhedralSurface"
    assert data["source"] == "postgis"

    # Verify standard GeoJSON coordinates structure
    geom = data["geometry"]
    assert geom["type"] == "MultiPolygon"
    assert len(geom["coordinates"]) == 6  # 6 faces of the 3D solid

    # Verify Z coordinates are preserved in the GeoJSON coordinates array
    first_polygon = geom["coordinates"][0][0]
    for pt in first_polygon:
        assert len(pt) == 3  # [lon, lat, elevation]
        assert isinstance(pt[2], (int, float))

    # Verify 3D bounding box
    bounds = data["bounds"]
    assert bounds["min_lon"] == 77.34
    assert bounds["max_lon"] == 77.36
    assert bounds["min_lat"] == 28.54
    assert bounds["max_lat"] == 28.56
    assert bounds["min_z"] == -5.0
    assert bounds["max_z"] == -2.0

    # Verify origin
    origin = data["origin"]
    assert origin["center_lon"] == pytest.approx(77.35, rel=1e-3)
    assert origin["center_lat"] == pytest.approx(28.55, rel=1e-3)
    assert origin["center_z"] == pytest.approx(-3.5, rel=1e-3)

    # Verify parent hierarchy geometry
    assert data["building"]["building_id"] == spatial_test_hierarchy["building"].building_id
    assert data["building"]["geometry"]["type"] == "Polygon"
    assert data["floor"]["floor_number"] == -2
    assert data["floor"]["geometry"]["type"] == "Polygon"
    assert data["parcel"]["parcel_id"] == spatial_test_hierarchy["parcel"].parcel_id
    assert data["parcel"]["geometry"]["type"] == "Polygon"

    # Verify security: No database credentials or internal SQL exposed
    raw_text = response.text.lower()
    assert "password" not in raw_text
    assert "postgresql://" not in raw_text
    assert "select " not in raw_text


def test_get_unit_geometry_missing_geometry(spatial_test_hierarchy):
    """Test unit that exists in database but has no registered PostGIS geometry."""
    unit_id = str(spatial_test_hierarchy["unit_no_geom"].id)
    response = client.get(f"/api/v1/spatial/unit/{unit_id}/geometry")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["unit_id"] == unit_id
    assert data["has_geometry"] is False
    assert data["geometry"] is None
    assert data["bounds"] is None
    assert "no 3D PostGIS geometry" in data["message"]


def test_get_unit_geometry_not_found():
    """Test requesting geometry for a non-existent unit UUID."""
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/spatial/unit/{random_uuid}/geometry")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_get_unit_geometry_malformed_uuid():
    """Test requesting geometry with an invalid UUID string."""
    response = client.get("/api/v1/spatial/unit/not-a-valid-uuid/geometry")

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Invalid unit UUID format" in data["error"]
