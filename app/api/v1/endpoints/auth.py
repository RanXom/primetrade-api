from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import (
    PasswordChange,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.user_service import (
    authenticate_user,
    change_password,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    update_user_last_login,
)

import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **username**: 3-50 chars, alphanumeric + underscore (must be unique)
    - **password**: Min 8 chars, must include upper, lower, digit
    - **full_name**: Optional display name
    """
    # Check uniqueness
    if await get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    if await get_user_by_username(db, data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    user = await create_user(db, data)
    return APIResponse(
        message="Account created successfully",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Login and get JWT tokens",
)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with email + password. Returns access and refresh tokens.
    """
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    await update_user_last_login(db, user)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "username": user.username},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return APIResponse(
        message="Login successful",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh access token",
)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    """
    user_id_str = verify_refresh_token(data.refresh_token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "username": user.username},
    )
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return APIResponse(
        message="Token refreshed",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Returns the authenticated user's profile. Requires Bearer token.
    """
    return APIResponse(data=UserResponse.model_validate(current_user))


@router.put(
    "/me/password",
    response_model=APIResponse,
    summary="Change current user's password",
)
async def change_my_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password. Requires current password verification.
    """
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password",
        )
    await change_password(db, current_user, data.new_password)
    return APIResponse(message="Password updated successfully")
