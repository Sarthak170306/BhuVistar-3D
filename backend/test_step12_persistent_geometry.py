"""
BhuVistaar 3D — Step 12 Persistent Geometry Seed & Verification Script
File: backend/test_step12_persistent_geometry.py

Creates or upserts a persistent cadastral hierarchy in PostgreSQL/PostGIS:
- Parcel: parcel_id = "55443322"
- Building: building_id = "B001"
- Floor: floor_number = -2, floor_name = "Basement 2"
- Unit: id = c1f7b4e2-8924-4d89-9a28-98e3b1c1e555, unit_code = "UP32", unit_type = "Parking Bay"
- Geometry: POLYHEDRALSURFACE Z (3D volumetric cuboid with elevation)
- ULPIN: BV3D-UP-NOI-55443322-B001-B02-UP32-PRK

DO NOT DELETE THE HIERARCHY AFTER EXECUTION.
It remains persisted in PostgreSQL so that frontend Cadastral3DViewer queries it directly.
"""

import json
import sys
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app
from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.ulpin_3d import ULPIN3D
from app.models.unit import Unit

UNIT_UUID = uuid.UUID("c1f7b4e2-8924-4d89-9a28-98e3b1c1e555")
PARCEL_ID = "55443322"
BUILDING_ID = "B001"
FLOOR_NUMBER = -2
FLOOR_NAME = "Basement 2"
UNIT_CODE = "UP32"
UNIT_TYPE = "Parking Bay"
ULPIN_CODE = "BV3D-UP-NOI-55443322-B001-B02-UP32-PRK"

# 3D PolyhedralSurface Z with 6 faces (sub-surface Basement 2: -6.0m to -3.5m)
WKT_POLYHEDRAL = """POLYHEDRALSURFACE Z (
    ((77.364 28.624 -6.0, 77.364 28.626 -6.0, 77.366 28.626 -6.0, 77.366 28.624 -6.0, 77.364 28.624 -6.0)),
    ((77.364 28.624 -3.5, 77.366 28.624 -3.5, 77.366 28.626 -3.5, 77.364 28.626 -3.5, 77.364 28.624 -3.5)),
    ((77.364 28.624 -6.0, 77.364 28.624 -3.5, 77.366 28.624 -3.5, 77.364 28.624 -6.0)),
    ((77.366 28.624 -6.0, 77.366 28.626 -6.0, 77.366 28.626 -3.5, 77.366 28.624 -3.5, 77.366 28.624 -6.0)),
    ((77.364 28.624 -6.0, 77.366 28.624 -6.0, 77.366 28.624 -3.5, 77.364 28.624 -3.5, 77.364 28.624 -6.0)),
    ((77.364 28.626 -6.0, 77.364 28.626 -3.5, 77.366 28.626 -3.5, 77.366 28.626 -6.0, 77.364 28.626 -6.0))
)"""

WKT_PARCEL = "POLYGON ((77.360 28.620, 77.360 28.630, 77.370 28.630, 77.370 28.620, 77.360 28.620))"
WKT_BUILDING = "POLYGON ((77.362 28.622, 77.362 28.628, 77.368 28.628, 77.368 28.622, 77.362 28.622))"
WKT_FLOOR = "POLYGON ((77.363 28.623, 77.363 28.627, 77.367 28.627, 77.367 28.623, 77.363 28.623))"


def seed_persistent_geometry():
    """Seeds or updates the Step 12 verification hierarchy in PostgreSQL/PostGIS."""
    print("=" * 60)
    print("SEEDING PERSISTENT STEP 12 GEOMETRY IN POSTGRESQL/POSTGIS")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Upsert Parcel
        parcel = db.query(Parcel).filter(Parcel.parcel_id == PARCEL_ID).first()
        if not parcel:
            parcel = Parcel(
                parcel_id=PARCEL_ID,
                state="UP",
                district="NOI",
                tehsil="Dadri",
                village="Chhajarsi",
                address="Sector 62 Institutional Cadastral Zone, Noida, UP",
                area_sq_m=Decimal("12500.00"),
                geometry=WKTElement(WKT_PARCEL, srid=4326),
            )
            db.add(parcel)
            db.flush()
            print(f"[+] Created Parcel: {parcel.parcel_id} (ID: {parcel.id})")
        else:
            parcel.geometry = WKTElement(WKT_PARCEL, srid=4326)
            db.flush()
            print(f"[*] Reusing existing Parcel: {parcel.parcel_id} (ID: {parcel.id})")

        # 2. Upsert Building
        building = db.query(Building).filter(Building.building_id == BUILDING_ID).first()
        if not building:
            building = Building(
                building_id=BUILDING_ID,
                parcel_id=parcel.id,
                name="BhuVistaar Institutional Tower B001",
                building_type="Mixed-Use Commercial & Residential",
                total_floors=12,
                height_m=Decimal("42.00"),
                geometry=WKTElement(WKT_BUILDING, srid=4326),
            )
            db.add(building)
            db.flush()
            print(f"[+] Created Building: {building.building_id} (ID: {building.id})")
        else:
            building.parcel_id = parcel.id
            building.geometry = WKTElement(WKT_BUILDING, srid=4326)
            db.flush()
            print(f"[*] Reusing existing Building: {building.building_id} (ID: {building.id})")

        # 3. Upsert Floor
        floor = (
            db.query(Floor)
            .filter(Floor.building_id == building.id, Floor.floor_number == FLOOR_NUMBER)
            .first()
        )
        if not floor:
            floor = Floor(
                building_id=building.id,
                floor_number=FLOOR_NUMBER,
                floor_name=FLOOR_NAME,
                elevation_m=Decimal("-6.00"),
                height_m=Decimal("2.80"),
                geometry=WKTElement(WKT_FLOOR, srid=4326),
            )
            db.add(floor)
            db.flush()
            print(f"[+] Created Floor: {floor.floor_name} (Number: {floor.floor_number}, ID: {floor.id})")
        else:
            floor.floor_name = FLOOR_NAME
            floor.elevation_m = Decimal("-6.00")
            floor.height_m = Decimal("2.80")
            floor.geometry = WKTElement(WKT_FLOOR, srid=4326)
            db.flush()
            print(f"[*] Reusing existing Floor: {floor.floor_name} (ID: {floor.id})")

        # 4. Upsert Unit with 3D POLYHEDRALSURFACE Z
        unit = db.query(Unit).filter(Unit.id == UNIT_UUID).first()
        if not unit:
            unit = Unit(
                id=UNIT_UUID,
                building_id=building.id,
                floor_id=floor.id,
                unit_code=UNIT_CODE,
                unit_type=UNIT_TYPE,
                usage_type="Vehicle Parking",
                area_sq_m=Decimal("28.50"),
                geometry=WKTElement(WKT_POLYHEDRAL, srid=4326),
            )
            db.add(unit)
            db.flush()
            print(f"[+] Created Unit: {unit.unit_code} (UUID: {unit.id})")
        else:
            unit.building_id = building.id
            unit.floor_id = floor.id
            unit.unit_code = UNIT_CODE
            unit.unit_type = UNIT_TYPE
            unit.geometry = WKTElement(WKT_POLYHEDRAL, srid=4326)
            db.flush()
            print(f"[*] Updated existing Unit: {unit.unit_code} (UUID: {unit.id})")

        # 5. Upsert ULPIN3D Record
        ulpin_record = db.query(ULPIN3D).filter(ULPIN3D.unit_id == unit.id).first()
        if not ulpin_record:
            ulpin_record = ULPIN3D(
                unit_id=unit.id,
                ulpin_3d=ULPIN_CODE,
                parcel_id_reference=parcel.parcel_id,
                building_id_reference=building.building_id,
                floor_number=floor.floor_number,
                unit_code=unit.unit_code,
                unit_type=unit.unit_type,
                generation_version="1.0",
            )
            db.add(ulpin_record)
            db.flush()
            print(f"[+] Created ULPIN3D Record: {ulpin_record.ulpin_3d}")
        else:
            ulpin_record.ulpin_3d = ULPIN_CODE
            ulpin_record.parcel_id_reference = parcel.parcel_id
            ulpin_record.building_id_reference = building.building_id
            ulpin_record.floor_number = floor.floor_number
            ulpin_record.unit_code = unit.unit_code
            ulpin_record.unit_type = unit.unit_type
            db.flush()
            print(f"[*] Updated existing ULPIN3D Record: {ulpin_record.ulpin_3d}")

        # Commit persistently to PostgreSQL
        db.commit()
        print("[OK] All records committed persistently to PostgreSQL.")
    except Exception as exc:
        db.rollback()
        print(f"[!] Error seeding persistent geometry: {exc}")
        raise
    finally:
        db.close()


def verify_geometry_serialization():
    """Verifies the GET /api/v1/spatial/unit/{unit_id}/geometry endpoint."""
    print("\n" + "=" * 60)
    print("VERIFYING POSTGIS GEOMETRY SERIALIZATION ENDPOINT")
    print("=" * 60)

    client = TestClient(app)
    url = f"/api/v1/spatial/unit/{UNIT_UUID}/geometry"
    print(f"Calling: GET {url}")

    res = client.get(url)
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}: {res.text}"
    body = res.json()

    print(f"HTTP Status: {res.status_code}")
    print(f"Success: {body.get('success')}")
    print(f"Has Geometry: {body.get('has_geometry')}")
    print(f"SRID: {body.get('srid')}")
    print(f"Geometry Type: {body.get('geometry_type')}")
    print(f"Geometry GeoJSON Type: {body.get('geometry', {}).get('type')}")

    # Requirement checks
    assert body["success"] is True, "Expected success=true"
    assert body["has_geometry"] is True, "Expected has_geometry=true"
    assert body["srid"] == 4326, "Expected srid=4326"
    assert body["geometry_type"] == "PolyhedralSurface", f"Expected geometry_type='PolyhedralSurface', got {body['geometry_type']}"
    assert body["geometry"]["type"] == "MultiPolygon", f"Expected geometry.type='MultiPolygon', got {body['geometry']['type']}"

    coords = body["geometry"]["coordinates"]
    assert len(coords) >= 4, f"Expected at least 4 faces, got {len(coords)}"
    sample_pt = coords[0][0][0]
    print(f"Sample 3D Coordinate: {sample_pt} (len={len(sample_pt)})")
    assert len(sample_pt) == 3, f"Expected 3D coordinates [lon, lat, elev], got {sample_pt}"
    print(f"  Longitude: {sample_pt[0]}")
    print(f"  Latitude:  {sample_pt[1]}")
    print(f"  Elevation: {sample_pt[2]}m")

    # Bounds check
    bounds = body.get("bounds", {})
    print(f"3D Bounds: Lon [{bounds.get('min_lon')}, {bounds.get('max_lon')}], Lat [{bounds.get('min_lat')}, {bounds.get('max_lat')}], Z [{bounds.get('min_z')}m, {bounds.get('max_z')}m]")
    assert bounds.get("min_z") is not None and bounds.get("max_z") is not None, "Missing vertical Z bounds"

    # Origin check
    origin = body.get("origin", {})
    print(f"Origin Centroid: Lon={origin.get('center_lon')}, Lat={origin.get('center_lat')}, Z={origin.get('center_z')}")

    # Hierarchy summaries
    print(f"Parent Building: {body.get('building', {}).get('building_id')}")
    print(f"Parent Floor: {body.get('floor', {}).get('floor_number')} ({body.get('floor', {}).get('floor_name')})")
    print(f"Parent Parcel: {body.get('parcel', {}).get('parcel_id')}")

    print("\n[OK] Requirement 6 VERIFIED: Endpoint returns valid 3D MultiPolygon coordinates from PostGIS.")
    return body


def verify_spatial_validation():
    """Verifies that spatial containment validation also succeeds for this unit."""
    print("\n" + "=" * 60)
    print("VERIFYING SPATIAL HIERARCHY VALIDATION ENDPOINT")
    print("=" * 60)

    client = TestClient(app)
    url = f"/api/v1/spatial/validate-unit/{UNIT_UUID}"
    print(f"Calling: GET {url}")

    res = client.get(url)
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}: {res.text}"
    body = res.json()

    print(f"Validation Valid: {body.get('valid')}")
    print(f"Checks: {json.dumps(body.get('checks'), indent=2)}")
    assert body["valid"] is True, "Expected valid=true"
    print("[OK] Spatial Containment Hierarchy VERIFIED: Unit contained in Building & Parcel.")


def verify_ulpin_lookup():
    """Verifies ULPIN lookup resolves to this unit."""
    print("\n" + "=" * 60)
    print("VERIFYING ULPIN LOOKUP ENDPOINT")
    print("=" * 60)

    client = TestClient(app)
    url = f"/api/v1/ulpin/{ULPIN_CODE}"
    print(f"Calling: GET {url}")

    res = client.get(url)
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["success"] is True
    assert body["data"]["unit_id"] == str(UNIT_UUID)
    print(f"ULPIN {ULPIN_CODE} successfully bound to Unit {UNIT_UUID}.")
    print("[OK] Authoritative ULPIN Record Lookup VERIFIED.")


if __name__ == "__main__":
    seed_persistent_geometry()
    geom_body = verify_geometry_serialization()
    verify_spatial_validation()
    verify_ulpin_lookup()
    print("\n" + "=" * 60)
    print("ALL STEP 12 PERSISTENT GEOMETRY VERIFICATIONS PASSED!")
    print("Record c1f7b4e2-8924-4d89-9a28-98e3b1c1e555 is permanently stored in PostgreSQL.")
    print("=" * 60)
