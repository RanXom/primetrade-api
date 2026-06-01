import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


# ─── Queries ──────────────────────────────────────────────────────────────────

async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID) -> Optional[Task]:
    result = await db.execute(
        select(Task).options(selectinload(Task.owner)).where(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def get_tasks(
    db: AsyncSession,
    owner_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    include_public: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Task], int]:
    query = select(Task).options(selectinload(Task.owner))
    count_query = select(func.count(Task.id))

    # Filter: owner or public tasks
    if owner_id is not None:
        if include_public:
            filter_expr = or_(Task.owner_id == owner_id, Task.is_public == True)  # noqa: E712
        else:
            filter_expr = Task.owner_id == owner_id
        query = query.where(filter_expr)
        count_query = count_query.where(filter_expr)
    elif include_public:
        query = query.where(Task.is_public == True)  # noqa: E712
        count_query = count_query.where(Task.is_public == True)  # noqa: E712

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)

    if search:
        search_filter = or_(
            Task.title.ilike(f"%{search}%"),
            Task.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return list(tasks), total


async def get_all_tasks_admin(
    db: AsyncSession,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Task], int]:
    query = select(Task).options(selectinload(Task.owner))
    count_query = select(func.count(Task.id))

    if user_id:
        query = query.where(Task.owner_id == user_id)
        count_query = count_query.where(Task.owner_id == user_id)

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)

    if search:
        search_filter = or_(
            Task.title.ilike(f"%{search}%"),
            Task.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return list(tasks), total


# ─── Mutations ────────────────────────────────────────────────────────────────

async def create_task(db: AsyncSession, data: TaskCreate, owner_id: uuid.UUID) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        is_public=data.is_public,
        due_date=data.due_date,
        owner_id=owner_id,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.flush()
