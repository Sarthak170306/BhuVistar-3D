from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role, require_roles
from app.auth.models import User, UserRole
from app.auth.schemas import (
    AuthMessageResponse,
    RoleTestResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.security import create_access_token
from app.auth.service import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)
from app.db.session import get_db

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Citizen User Registration",
    description=(
        "Registers a new citizen user. Public registration strictly enforces the CITIZEN role. "
        "Requests attempting to register as OFFICIAL or ADMIN are unconditionally assigned CITIZEN."
    ),
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """
    Public registration endpoint. Always assigns UserRole.CITIZEN.
    """
    try:
        user = create_user(
            db=db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=UserRole.CITIZEN,  # Enforce CITIZEN role strictly
        )
        return user
    except DuplicateEmailError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates credentials and returns a signed JWT access token with role metadata.",
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Validates user credentials and issues a cryptographic JWT bearer token.
    """
    try:
        user = authenticate_user(
            db=db,
            email=payload.email,
            password=payload.password,
        )
    except (InvalidCredentialsError, InactiveUserError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile",
    description="Returns the profile and role of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Resolves the identity and role from the validated JWT token.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout User",
    description=(
        "Acknowledges client-side logout. With stateless JWT authentication, the client must discard "
        "the locally stored access token. No server-side session invalidation is fabricated."
    ),
)
def logout(
    current_user: User = Depends(get_current_user),
) -> AuthMessageResponse:
    """
    Client-side token disposal acknowledgement.
    """
    return AuthMessageResponse(
        success=True,
        message="Successfully logged out. Client token has been discarded.",
    )


@router.get(
    "/official-test",
    response_model=RoleTestResponse,
    status_code=status.HTTP_200_OK,
    summary="RBAC Official Test Endpoint",
    description="Protected test endpoint accessible only to users with OFFICIAL or ADMIN roles. CITIZEN returns 403.",
)
def official_test(
    current_user: User = Depends(require_roles(UserRole.OFFICIAL, UserRole.ADMIN)),
) -> RoleTestResponse:
    """
    Role-verified endpoint for Official and Admin accounts.
    """
    role_str = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    return RoleTestResponse(
        success=True,
        message=f"Access granted to official resource for role '{role_str}'.",
        role=role_str,
        user_id=current_user.id,
        email=current_user.email,
    )


@router.get(
    "/admin-test",
    response_model=RoleTestResponse,
    status_code=status.HTTP_200_OK,
    summary="RBAC Admin Test Endpoint",
    description="Protected test endpoint accessible strictly to users with the ADMIN role. Others return 403.",
)
def admin_test(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RoleTestResponse:
    """
    Role-verified endpoint strictly for Administrator accounts.
    """
    role_str = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    return RoleTestResponse(
        success=True,
        message=f"Access granted to admin resource for role '{role_str}'.",
        role=role_str,
        user_id=current_user.id,
        email=current_user.email,
    )
