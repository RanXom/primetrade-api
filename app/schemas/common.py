from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: Optional[T] = None


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[list[ErrorDetail]] = None
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
