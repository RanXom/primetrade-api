from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({"field": field or None, "message": error["msg"]})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validation failed",
                "errors": errors,
                "error_code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning(f"DB IntegrityError: {exc.orig}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "message": "A resource with the provided data already exists",
                "error_code": "CONFLICT",
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": f"Route {request.url.path} not found",
                "error_code": "NOT_FOUND",
            },
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        logger.error(f"Internal server error on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An unexpected error occurred. Please try again later.",
                "error_code": "INTERNAL_ERROR",
            },
        )
