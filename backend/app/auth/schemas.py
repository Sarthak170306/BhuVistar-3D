import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.models import UserRole


class UserRegisterRequest(BaseModel):
    """
    Schema for citizen public registration.
    Public registration is strictly restricted to CITIZEN role.
    """
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=255, description="Full legal name of the user")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, max_length=128, description="Plaintext password (min 6 characters)")
    # Optional role field included in case client submits it; will be strictly enforced to CITIZEN by backend
    role: Optional[str] = Field(default=None, description="Requested role (ignored; public registration is CITIZEN only)")


class UserLoginRequest(BaseModel):
    """
    Schema for authentication credentials.
    """
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Plaintext password")


class UserResponse(BaseModel):
    """
    Public representation of a user. Never exposes password hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """
    OAuth2-compatible Bearer JWT token response.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuthMessageResponse(BaseModel):
    """
    Generic message response for auth operations such as logout.
    """
    success: bool = True
    message: str


class RoleTestResponse(BaseModel):
    """
    Response schema for RBAC protected test endpoints.
    """
    success: bool = True
    message: str
    role: str
    user_id: uuid.UUID
    email: str
