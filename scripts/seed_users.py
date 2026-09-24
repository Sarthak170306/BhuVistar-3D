"""
BhuVistaar 3D — User Seeding & Role Management CLI
Controlled administrative utility for provisioning Official, Admin, and Citizen accounts.

Usage:
    python scripts/seed_users.py
    python scripts/seed_users.py --email custom@gov.in --name "Custom Official" --role OFFICIAL --password "Secret@123"
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.auth.models import User, UserRole
from app.auth.security import hash_password
from app.auth.service import get_user_by_email
from app.db.session import SessionLocal

DEMO_ACCOUNTS = [
    {
        "name": "Citizen Ramesh Kumar",
        "email": "citizen@bhuvistaar.gov.in",
        "password": "Citizen@2026",
        "role": UserRole.CITIZEN,
    },
    {
        "name": "Noida Cadastral Officer Priya Sharma",
        "email": "official@bhuvistaar.gov.in",
        "password": "Official@2026",
        "role": UserRole.OFFICIAL,
    },
    {
        "name": "Chief Cadastral Administrator Vikram Singh",
        "email": "admin@bhuvistaar.gov.in",
        "password": "Admin@2026",
        "role": UserRole.ADMIN,
    },
]


def seed_or_update_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: UserRole,
) -> User:
    clean_email = email.strip().lower()
    existing_user = get_user_by_email(db, clean_email)

    if existing_user:
        existing_user.name = name
        existing_user.password_hash = hash_password(password)
        existing_user.role = role
        existing_user.is_active = True
        db.commit()
        db.refresh(existing_user)
        print(f"[UPDATED] User {clean_email} -> Role: {role.value}")
        return existing_user
    else:
        new_user = User(
            name=name,
            email=clean_email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"[CREATED] User {clean_email} -> Role: {role.value} (ID: {new_user.id})")
        return new_user


def main() -> None:
    parser = argparse.ArgumentParser(description="BhuVistaar 3D User Management and Seeding Tool")
    parser.add_argument("--name", type=str, help="Full name of user")
    parser.add_argument("--email", type=str, help="Email address of user")
    parser.add_argument("--password", type=str, help="Password for user")
    parser.add_argument(
        "--role",
        type=str,
        choices=["CITIZEN", "OFFICIAL", "ADMIN"],
        help="Institutional role to assign",
    )

    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.email and args.password:
            name = args.name or args.email.split("@")[0].capitalize()
            role_enum = UserRole(args.role.upper()) if args.role else UserRole.CITIZEN
            seed_or_update_user(db, name, args.email, args.password, role_enum)
        else:
            print("==================================================")
            print("SEEDING DEFAULT BHUVISTAAR 3D DEMO ACCOUNTS")
            print("==================================================")
            for acc in DEMO_ACCOUNTS:
                seed_or_update_user(
                    db=db,
                    name=acc["name"],
                    email=acc["email"],
                    password=acc["password"],
                    role=acc["role"],
                )
            print("==================================================")
            print("Demo accounts ready:")
            for acc in DEMO_ACCOUNTS:
                print(f"- {acc['role'].value}: {acc['email']} / {acc['password']}")
            print("==================================================")
    finally:
        db.close()


if __name__ == "__main__":
    main()
