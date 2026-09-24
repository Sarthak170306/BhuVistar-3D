from enum import Enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, Enum):
    """
    Role definitions for BhuVistaar 3D access control.
    """
    CITIZEN = "CITIZEN"
    OFFICIAL = "OFFICIAL"
    ADMIN = "ADMIN"


class User(Base):
    """
    Persistent user entity supporting Citizen, Official, and Admin roles.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full legal name of the user",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Authoritative email address used for authentication",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Secure bcrypt hashed password",
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            native_enum=False,
            length=20,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=UserRole.CITIZEN,
        nullable=False,
        comment="User role: CITIZEN, OFFICIAL, ADMIN",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating active account status",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
