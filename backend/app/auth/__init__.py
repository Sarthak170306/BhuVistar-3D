from app.auth.models import User, UserRole
from app.auth.schemas import (
    AuthMessageResponse,
    RoleTestResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.security import create_access_token, decode_access_token, hash_password, verify_password
from app.auth.service import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from app.auth.dependencies import get_current_user, require_role, require_roles

__all__ = [
    "User",
    "UserRole",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "TokenResponse",
    "AuthMessageResponse",
    "RoleTestResponse",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "authenticate_user",
    "DuplicateEmailError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "get_current_user",
    "require_role",
    "require_roles",
]
