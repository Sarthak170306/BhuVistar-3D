import json
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.models.building import Building
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.unit import Unit


def serialize_unit_geometry(db: Session, unit_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Queries and serializes authoritative 3D spatial geometry for a cadastral Unit
    and its hierarchical parents (Building, Floor, Parcel) from PostgreSQL/PostGIS.

    - Preserves 3D coordinates [longitude, latitude, elevation_z] in EPSG:4326.
    - Handles POLYHEDRALSURFACE Z by dumping constituent polygon faces into standard 3D MultiPolygon GeoJSON.
    - Handles POLYGON Z directly via PostGIS ST_AsGeoJSON.
    - Calculates 3D bounding envelope (ST_XMin/Max, ST_YMin/Max, ST_ZMin/Max).
    - Derives metric centroid / origin for Three.js local Cartesian conversion.
    - Returns None if unit_id does not exist.
    """
    # 1. Query unit with parent relationships
    unit = (
        db.query(Unit)
        .options(
            joinedload(Unit.floor),
            joinedload(Unit.building).joinedload(Building.parcel),
        )
        .filter(Unit.id == unit_id)
        .first()
    )

    if not unit:
        return None

    # 2. Extract parent building summary
    building_summary = None
    if unit.building:
        b = unit.building
        b_geom = None
        if b.geometry is not None:
            b_json = db.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM buildings WHERE id = :bid"),
                {"bid": b.id},
            ).scalar()
            if b_json:
                b_geom = json.loads(b_json)

        building_summary = {
            "building_id": b.building_id,
            "name": b.name,
            "height_m": float(b.height_m) if b.height_m is not None else None,
            "total_floors": b.total_floors,
            "geometry": b_geom,
        }

    # 3. Extract parent floor summary
    floor_summary = None
    if unit.floor:
        f = unit.floor
        f_geom = None
        if f.geometry is not None:
            f_json = db.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM floors WHERE id = :fid"),
                {"fid": f.id},
            ).scalar()
            if f_json:
                f_geom = json.loads(f_json)

        floor_summary = {
            "floor_number": f.floor_number,
            "floor_name": f.floor_name,
            "elevation_m": float(f.elevation_m) if f.elevation_m is not None else None,
            "height_m": float(f.height_m) if f.height_m is not None else None,
            "geometry": f_geom,
        }

    # 4. Extract parent parcel summary
    parcel_summary = None
    if unit.building and unit.building.parcel:
        p = unit.building.parcel
        p_geom = None
        if p.geometry is not None:
            p_json = db.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM parcels WHERE id = :pid"),
                {"pid": p.id},
            ).scalar()
            if p_json:
                p_geom = json.loads(p_json)

        parcel_summary = {
            "parcel_id": p.parcel_id,
            "state": p.state,
            "district": p.district,
            "geometry": p_geom,
        }

    # 5. Handle case where unit exists but has no geometry
    if unit.geometry is None:
        return {
            "success": True,
            "unit_id": str(unit.id),
            "srid": 4326,
            "geometry_type": None,
            "has_geometry": False,
            "geometry": None,
            "building": building_summary,
            "floor": floor_summary,
            "parcel": parcel_summary,
            "bounds": None,
            "vertical_range": None,
            "origin": None,
            "source": "postgis",
            "message": "Unit record exists, but no 3D PostGIS geometry has been registered.",
            "detail": "Demonstration volumetric geometry remains active as fallback.",
        }

    # 6. Query geometry type in PostGIS
    gtype_raw = db.execute(
        text("SELECT ST_GeometryType(geometry) FROM units WHERE id = :uid"),
        {"uid": unit.id},
    ).scalar()
    geom_type = gtype_raw.replace("ST_", "") if gtype_raw else "Unknown"

    # 7. Serialize unit 3D geometry
    if "PolyhedralSurface" in (gtype_raw or ""):
        # Standard GeoJSON does not support PolyhedralSurface directly;
        # ST_Dump faces and ST_Collect as MultiPolygon with 3D [x, y, z] coordinates
        geojson_str = db.execute(
            text("""
                SELECT ST_AsGeoJSON(ST_Collect((dp).geom))
                FROM (SELECT ST_Dump(geometry) as dp FROM units WHERE id = :uid) sub
            """),
            {"uid": unit.id},
        ).scalar()
    else:
        geojson_str = db.execute(
            text("SELECT ST_AsGeoJSON(geometry) FROM units WHERE id = :uid"),
            {"uid": unit.id},
        ).scalar()

    unit_geom_data = json.loads(geojson_str) if geojson_str else None

    # 8. Query 3D bounding box coordinates
    bbox_row = db.execute(
        text("""
            SELECT 
                ST_XMin(geometry) as min_x, ST_XMax(geometry) as max_x,
                ST_YMin(geometry) as min_y, ST_YMax(geometry) as max_y,
                ST_ZMin(geometry) as min_z, ST_ZMax(geometry) as max_z
            FROM units WHERE id = :uid
        """),
        {"uid": unit.id},
    ).mappings().one()

    min_x = float(bbox_row["min_x"]) if bbox_row["min_x"] is not None else None
    max_x = float(bbox_row["max_x"]) if bbox_row["max_x"] is not None else None
    min_y = float(bbox_row["min_y"]) if bbox_row["min_y"] is not None else None
    max_y = float(bbox_row["max_y"]) if bbox_row["max_y"] is not None else None
    min_z = float(bbox_row["min_z"]) if bbox_row["min_z"] is not None else None
    max_z = float(bbox_row["max_z"]) if bbox_row["max_z"] is not None else None

    bounds = {
        "min_lon": min_x,
        "max_lon": max_x,
        "min_lat": min_y,
        "max_lat": max_y,
        "min_z": min_z,
        "max_z": max_z,
    }

    origin = {
        "center_lon": (min_x + max_x) / 2.0 if min_x is not None and max_x is not None else None,
        "center_lat": (min_y + max_y) / 2.0 if min_y is not None and max_y is not None else None,
        "center_z": (min_z + max_z) / 2.0 if min_z is not None and max_z is not None else (
            float(unit.floor.elevation_m) if unit.floor and unit.floor.elevation_m is not None else 0.0
        ),
    }

    vertical_range = {
        "min_z": min_z,
        "max_z": max_z,
        "elevation_datum": "MSL",
    }

    return {
        "success": True,
        "unit_id": str(unit.id),
        "srid": 4326,
        "geometry_type": geom_type,
        "has_geometry": unit_geom_data is not None,
        "geometry": unit_geom_data,
        "building": building_summary,
        "floor": floor_summary,
        "parcel": parcel_summary,
        "bounds": bounds,
        "vertical_range": vertical_range,
        "origin": origin,
        "source": "postgis",
        "message": "Authoritative PostGIS geometry serialized successfully.",
        "detail": f"Type: {geom_type}, SRID: 4326, Z-Range: {min_z}m to {max_z}m.",
    }
