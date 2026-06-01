import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserRegister, UserUpdate, UserAdminUpdate


# ─── Queries ──────────────────────────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username.lower()))
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        filter_expr = or_(
            User.email.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
        )
        query = query.where(filter_expr)
        count_query = count_query.where(filter_expr)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return list(users), total


# ─── Mutations ────────────────────────────────────────────────────────────────

async def create_user(db: AsyncSession, data: UserRegister) -> User:
    user = User(
        email=data.email.lower(),
        username=data.username.lower(),
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role="user",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_admin_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
) -> User:
    user = User(
        email=email.lower(),
        username=username.lower(),
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        # Constant-time comparison to prevent timing attacks
        verify_password("dummy", get_password_hash("dummy"))
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user_last_login(db: AsyncSession, user: User) -> None:
    user.last_login = datetime.now(timezone.utc)
    await db.flush()


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "username" and value:
            value = value.lower()
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def admin_update_user(db: AsyncSession, user: User, data: UserAdminUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "username" and value:
            value = value.lower()
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.hashed_password = get_password_hash(new_password)
    await db.flush()


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.flush()
