import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, get_current_admin, get_optional_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import (
    create_task,
    delete_task,
    get_all_tasks_admin,
    get_task_by_id,
    get_tasks,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ─── User Task Endpoints ──────────────────────────────────────────────────────

@router.get(
    "",
    response_model=APIResponse[TaskListResponse],
    summary="List current user's tasks",
)
async def list_my_tasks(
    status: Optional[str] = Query(None, pattern=r"^(todo|in_progress|done|cancelled)$"),
    priority: Optional[str] = Query(None, pattern=r"^(low|medium|high|urgent)$"),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tasks belonging to the authenticated user, with optional filters."""
    tasks, total = await get_tasks(
        db,
        owner_id=current_user.id,
        status=status,
        priority=priority,
        search=search,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
    )


@router.post(
    "",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_my_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task owned by the authenticated user."""
    task = await create_task(db, data, current_user.id)
    return APIResponse(
        message="Task created successfully",
        data=TaskResponse.model_validate(task),
    )


@router.get(
    "/public",
    response_model=APIResponse[TaskListResponse],
    summary="List public tasks (no auth required)",
)
async def list_public_tasks(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all public tasks. No authentication required."""
    tasks, total = await get_tasks(
        db,
        include_public=True,
        search=search,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
    )


@router.get(
    "/{task_id}",
    response_model=APIResponse[TaskResponse],
    summary="Get a task by ID",
)
async def get_task(
    task_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a task by ID.
    - Public tasks are accessible to anyone.
    - Private tasks require ownership or admin role.
    """
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if not task.is_public:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if current_user.role != "admin" and task.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return APIResponse(data=TaskResponse.model_validate(task))


@router.patch(
    "/{task_id}",
    response_model=APIResponse[TaskResponse],
    summary="Update a task",
)
async def update_my_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task. Users can only update their own tasks. Admins can update any task."""
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.role != "admin" and task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own tasks")

    updated_task = await update_task(db, task, data)
    return APIResponse(
        message="Task updated successfully",
        data=TaskResponse.model_validate(updated_task),
    )


@router.delete(
    "/{task_id}",
    response_model=APIResponse,
    summary="Delete a task",
)
async def delete_my_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task. Users can only delete their own tasks. Admins can delete any task."""
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.role != "admin" and task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own tasks")

    await delete_task(db, task)
    return APIResponse(message="Task deleted successfully")


# ─── Admin Task Endpoints ─────────────────────────────────────────────────────

@router.get(
    "/admin/all",
    response_model=APIResponse[TaskListResponse],
    summary="[Admin] List all tasks",
)
async def admin_list_all_tasks(
    status: Optional[str] = Query(None, pattern=r"^(todo|in_progress|done|cancelled)$"),
    priority: Optional[str] = Query(None, pattern=r"^(low|medium|high|urgent)$"),
    search: Optional[str] = Query(None, max_length=100),
    user_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """[Admin only] List all tasks across all users, with optional filters."""
    tasks, total = await get_all_tasks_admin(
        db,
        status=status,
        priority=priority,
        search=search,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
    )
