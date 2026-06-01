import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: str = Field("todo", pattern=r"^(todo|in_progress|done|cancelled)$")
    priority: str = Field("medium", pattern=r"^(low|medium|high|urgent)$")
    is_public: bool = False
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field(None, pattern=r"^(todo|in_progress|done|cancelled)$")
    priority: Optional[str] = Field(None, pattern=r"^(low|medium|high|urgent)$")
    is_public: Optional[bool] = None
    due_date: Optional[datetime] = None


class TaskFilters(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ─── Response Schemas ─────────────────────────────────────────────────────────


class TaskOwnerInfo(BaseModel):
    id: uuid.UUID
    username: str
    full_name: Optional[str]

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    is_public: bool
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    owner_id: uuid.UUID
    owner: Optional[TaskOwnerInfo] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
