import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.auth.security import create_access_token, verify_password
from app.auth.service import create_user, get_user_by_email
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def db():
    """Provides a transactional database session for tests."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cleanup_users(db: Session):
    """Tracks and cleans up created test users after each test."""
    created_emails: list[str] = []

    def _track(email: str):
        created_emails.append(email.lower())
        return email

    yield _track

    for email in created_emails:
        db.execute(delete(User).where(User.email == email))
    db.commit()


# 1. Citizen registration
def test_citizen_registration(cleanup_users, db: Session):
    test_email = cleanup_users(f"citizen_{uuid.uuid4().hex[:8]}@example.com")
    payload = {
        "name": "Aarav Sharma",
        "email": test_email,
        "password": "Password@123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Aarav Sharma"
    assert data["email"] == test_email
    assert data["role"] == "CITIZEN"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "id" in data

    # Verify persistent record in DB
    user = get_user_by_email(db, test_email)
    assert user is not None
    assert user.role == UserRole.CITIZEN


# 2. Duplicate email rejection
def test_duplicate_email_rejection(cleanup_users):
    test_email = cleanup_users(f"dup_{uuid.uuid4().hex[:8]}@example.com")
    payload = {
        "name": "Original User",
        "email": test_email,
        "password": "Password@123",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate registration with same email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


# 3. Password hashing
def test_password_hashing(cleanup_users, db: Session):
    test_email = cleanup_users(f"hash_{uuid.uuid4().hex[:8]}@example.com")
    raw_password = "SecureGovPass#2026"
    payload = {
        "name": "Hashing Test User",
        "email": test_email,
        "password": raw_password,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    user = get_user_by_email(db, test_email)
    assert user is not None
    # Password must NEVER be stored in plain text
    assert user.password_hash != raw_password
    assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
    assert verify_password(raw_password, user.password_hash) is True
    assert verify_password("WrongPassword!", user.password_hash) is False


# 4. Successful login
def test_successful_login(cleanup_users):
    test_email = cleanup_users(f"login_{uuid.uuid4().hex[:8]}@example.com")
    reg_payload = {
        "name": "Login Test User",
        "email": test_email,
        "password": "CorrectPassword#123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": test_email,
        "password": "CorrectPassword#123",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == test_email
    assert data["user"]["role"] == "CITIZEN"


# 5. Wrong password
def test_wrong_password(cleanup_users):
    test_email = cleanup_users(f"wrongpw_{uuid.uuid4().hex[:8]}@example.com")
    reg_payload = {
        "name": "Wrong PW User",
        "email": test_email,
        "password": "CorrectPassword#123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login with incorrect password
    response = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "IncorrectPassword999",
    })
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()

    # Login with non-existent email
    response_nonexistent = client.post("/api/v1/auth/login", json={
        "email": "doesnotexist@example.com",
        "password": "SomePassword#123",
    })
    assert response_nonexistent.status_code == 401


# 6. Invalid JWT
def test_invalid_jwt():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.signature.token"},
    )
    assert response.status_code == 401
    assert "invalid authentication token" in response.json()["detail"].lower()


# 7. Expired JWT
def test_expired_jwt(cleanup_users, db: Session):
    test_email = cleanup_users(f"expired_{uuid.uuid4().hex[:8]}@example.com")
    user = create_user(db, "Expired User", test_email, "Password@123", UserRole.CITIZEN)

    # Create expired token
    expired_token, _ = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        expires_delta=timedelta(seconds=-10),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# 8. /auth/me
def test_auth_me(cleanup_users, db: Session):
    test_email = cleanup_users(f"me_{uuid.uuid4().hex[:8]}@example.com")
    user = create_user(db, "Me Test User", test_email, "Password@123", UserRole.CITIZEN)

    token, _ = create_access_token(user.id, user.email, user.role.value)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == test_email
    assert data["name"] == "Me Test User"
    assert data["role"] == "CITIZEN"


# 9. Citizen access
def test_citizen_access(cleanup_users, db: Session):
    test_email = cleanup_users(f"citizen_access_{uuid.uuid4().hex[:8]}@example.com")
    user = create_user(db, "Regular Citizen", test_email, "Password@123", UserRole.CITIZEN)

    token, _ = create_access_token(user.id, user.email, user.role.value)
    # Citizen can access /me
    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200

    # Citizen can access logout
    res_logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res_logout.status_code == 200
    assert res_logout.json()["success"] is True


# 10. Official access
def test_official_access(cleanup_users, db: Session):
    test_email = cleanup_users(f"official_{uuid.uuid4().hex[:8]}@example.com")
    official_user = create_user(db, "Cadastral Officer", test_email, "Password@123", UserRole.OFFICIAL)

    token, _ = create_access_token(official_user.id, official_user.email, official_user.role.value)
    response = client.get(
        "/api/v1/auth/official-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["role"] == "OFFICIAL"


# 11. Admin access
def test_admin_access(cleanup_users, db: Session):
    test_email = cleanup_users(f"admin_{uuid.uuid4().hex[:8]}@example.com")
    admin_user = create_user(db, "System Administrator", test_email, "Password@123", UserRole.ADMIN)

    token, _ = create_access_token(admin_user.id, admin_user.email, admin_user.role.value)

    # Admin can access official endpoint
    res_off = client.get("/api/v1/auth/official-test", headers={"Authorization": f"Bearer {token}"})
    assert res_off.status_code == 200

    # Admin can access admin endpoint
    res_admin = client.get("/api/v1/auth/admin-test", headers={"Authorization": f"Bearer {token}"})
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "ADMIN"


# 12. Citizen blocked from official endpoint -> 403
def test_citizen_blocked_from_official_endpoint(cleanup_users, db: Session):
    test_email = cleanup_users(f"citizen_blocked_{uuid.uuid4().hex[:8]}@example.com")
    citizen_user = create_user(db, "Citizen User", test_email, "Password@123", UserRole.CITIZEN)

    token, _ = create_access_token(citizen_user.id, citizen_user.email, citizen_user.role.value)
    response = client.get(
        "/api/v1/auth/official-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "insufficient permissions" in response.json()["detail"].lower()


# 13. Official blocked from admin endpoint -> 403
def test_official_blocked_from_admin_endpoint(cleanup_users, db: Session):
    test_email = cleanup_users(f"off_blocked_{uuid.uuid4().hex[:8]}@example.com")
    official_user = create_user(db, "Cadastral Officer", test_email, "Password@123", UserRole.OFFICIAL)

    token, _ = create_access_token(official_user.id, official_user.email, official_user.role.value)
    response = client.get(
        "/api/v1/auth/admin-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "insufficient permissions" in response.json()["detail"].lower()


# 14. Public registration cannot create OFFICIAL
def test_public_registration_cannot_create_official(cleanup_users, db: Session):
    test_email = cleanup_users(f"spoofed_{uuid.uuid4().hex[:8]}@example.com")
    payload = {
        "name": "Malicious Spoof Attempt",
        "email": test_email,
        "password": "Password@123",
        "role": "OFFICIAL",  # Attacker attempts to grant themselves OFFICIAL role
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "CITIZEN"  # Must unconditionally remain CITIZEN

    # Verify in DB
    user = get_user_by_email(db, test_email)
    assert user is not None
    assert user.role == UserRole.CITIZEN


# 15. Inactive user rejection
def test_inactive_user_rejected(cleanup_users, db: Session):
    test_email = cleanup_users(f"inactive_{uuid.uuid4().hex[:8]}@example.com")
    user = create_user(db, "Inactive User", test_email, "Password@123", UserRole.CITIZEN, is_active=False)

    # Login rejection
    res_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "Password@123"})
    assert res_login.status_code == 401
    assert "inactive" in res_login.json()["detail"].lower()

    # Token rejection
    token, _ = create_access_token(user.id, user.email, user.role.value)
    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 403
