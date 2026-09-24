import uuid
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.auth.security import hash_password, verify_password


class DuplicateEmailError(Exception):
    """Raised when an account already exists with the given email address."""
    pass


class InactiveUserError(Exception):
    """Raised when the user account is deactivated."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when authentication credentials fail validation."""
    pass


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Look up a user by canonical lowercased email address.
    """
    clean_email = email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """
    Look up a user by primary key UUID.
    """
    stmt = select(User).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: UserRole = UserRole.CITIZEN,
    is_active: bool = True,
) -> User:
    """
    Creates a new user record with securely hashed password.
    Raises DuplicateEmailError if an account with this email exists.
    """
    clean_email = email.strip().lower()
    existing = get_user_by_email(db, clean_email)
    if existing:
        raise DuplicateEmailError(f"User with email '{clean_email}' already exists.")

    hashed_pw = hash_password(password)
    user = User(
        name=name.strip(),
        email=clean_email,
        password_hash=hashed_pw,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User:
    """
    Verifies user credentials.
    Raises InvalidCredentialsError on bad email or wrong password.
    Raises InactiveUserError if user account is deactivated.
    """
    user = get_user_by_email(db, email)
    if not user:
        raise InvalidCredentialsError("Invalid email or password.")

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password.")

    if not user.is_active:
        raise InactiveUserError("User account is inactive. Please contact administration.")

    return user
