import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import UserAdminUpdate, UserListResponse, UserResponse
from app.services.user_service import (
    admin_update_user,
    delete_user,
    get_user_by_id,
    get_users,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=APIResponse[dict],
    summary="[Admin] List all users",
)
async def admin_list_users(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin only] List all registered users."""
    users, total = await get_users(db, page=page, page_size=page_size, search=search)
    return APIResponse(
        data={
            "users": [UserListResponse.model_validate(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total else 0,
        }
    )


@router.get(
    "/users/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="[Admin] Get a user by ID",
)
async def admin_get_user(
    user_id: uuid.UUID,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin only] Retrieve any user by their ID."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return APIResponse(data=UserResponse.model_validate(user))


@router.patch(
    "/users/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="[Admin] Update a user",
)
async def admin_update_user_endpoint(
    user_id: uuid.UUID,
    data: UserAdminUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin only] Update any user's profile, role, or active status."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-demotion from admin
    if user.id == current_admin.id and data.role == "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot demote yourself from admin",
        )

    updated_user = await admin_update_user(db, user, data)
    return APIResponse(
        message="User updated successfully",
        data=UserResponse.model_validate(updated_user),
    )


@router.delete(
    "/users/{user_id}",
    response_model=APIResponse,
    summary="[Admin] Delete a user",
)
async def admin_delete_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin only] Permanently delete a user and all their tasks."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await delete_user(db, user)
    return APIResponse(message=f"User '{user.username}' deleted successfully")
