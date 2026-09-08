import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_ulpin_success():
    """
    Test successful generation of 3D ULPIN via POST /api/v1/ulpin/generate
    using the exact prompt payload.
    """
    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": "55443322",
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["ulpin_3d"] == "BV3D-UP-NOI-55443322-B001-B02-UP32-PRK"


def test_generate_ulpin_residential():
    """
    Test residential unit with integer floor and unit numbers.
    """
    payload = {
        "state": "UP",
        "district": "LKO",
        "parcel": "12345678",
        "building": "B001",
        "floor": 4,
        "unit": 402,
        "type": "RES",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["ulpin_3d"] == "BV3D-UP-LKO-12345678-B001-F04-U402-RES"


def test_generate_ulpin_property_type_alias():
    """
    Test alias support for property_type in the request body.
    """
    payload = {
        "state": "KA",
        "district": "BLR",
        "parcel": "87654321",
        "building": "B002",
        "floor": 0,
        "unit": 12,
        "property_type": "COM",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["ulpin_3d"] == "BV3D-KA-BLR-87654321-B002-F00-U012-COM"


def test_generate_ulpin_invalid_state():
    """
    Test validation failure when state code is invalid (HTTP 400).
    """
    payload = {
        "state": "INVALID_STATE",
        "district": "NOI",
        "parcel": "55443322",
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "State must contain exactly 2 uppercase alphabetic characters" in data["error"]


def test_generate_ulpin_invalid_building():
    """
    Test validation failure when building code does not match Bxxx.
    """
    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": "55443322",
        "building": "Tower",
        "floor": "B02",
        "unit": "UP32",
        "type": "PRK",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Building must follow Bxxx format" in data["error"]


def test_generate_ulpin_invalid_property_type():
    """
    Test validation failure when unsupported property type is supplied.
    """
    payload = {
        "state": "UP",
        "district": "NOI",
        "parcel": "55443322",
        "building": "B001",
        "floor": "B02",
        "unit": "UP32",
        "type": "INVALID_TYPE",
    }
    response = client.post("/api/v1/ulpin/generate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Unsupported property type" in data["error"]


def test_generate_ulpin_missing_fields():
    """
    Test 422 Unprocessable Entity when required fields are missing.
    """
    response = client.post("/api/v1/ulpin/generate", json={})
    assert response.status_code == 422


def test_existing_health_endpoint():
    """
    Test that existing /health route is unaffected.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
