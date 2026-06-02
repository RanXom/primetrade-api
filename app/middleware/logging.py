import time
from fastapi import FastAPI, Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        # Extract request info
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.status_code

            log_fn = logger.info if status_code < 400 else logger.warning
            log_fn(
                f"{method} {url} | {status_code} | {duration_ms:.1f}ms | {client_ip}"
            )
            response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"{method} {url} | 500 | {duration_ms:.1f}ms | {client_ip} | ERROR: {exc}"
            )
            raise


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
