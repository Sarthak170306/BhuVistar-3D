import uuid
from typing import Callable, Optional, Sequence
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from app.auth.models import User, UserRole
from app.auth.security import decode_access_token
from app.auth.service import get_user_by_id
from app.db.session import get_db

# Optional HTTPBearer to handle credentials gracefully with custom error formatting
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts, verifies, and resolves the current authenticated user.
    Validates:
    - Presence of Bearer token
    - Cryptographic signature
    - Token expiration
    - User existence in database
    - Active account status
    """
    token: str | None = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback manual inspection of Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing user subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier format in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Access denied.",
        )

    return user


def require_roles(*allowed_roles: UserRole | str) -> Callable[[User], User]:
    """
    Factory dependency creating a role-checker for one or multiple allowed roles.
    Raises HTTP 403 Forbidden if user role is not authorized.
    """
    # Normalize roles to string values
    role_values = {r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles}

    def _role_checker(user: User = Depends(get_current_user)) -> User:
        user_role_val = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        if user_role_val not in role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Insufficient permissions. Required: {', '.join(sorted(role_values))}.",
            )
        return user

    return _role_checker


def require_role(role: UserRole | str) -> Callable[[User], User]:
    """
    Factory dependency enforcing a single specific role.
    """
    return require_roles(role)
