from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import create_tables
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.logging import register_middleware
from app.schemas.common import HealthResponse

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} starting up...")
    logger.info(f"   Environment : {settings.environment}")
    logger.info(f"   Debug mode  : {settings.debug}")

    # Create database tables
    try:
        await create_tables()
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    yield

    logger.info("⏹️  Application shutting down")


# ─── App Factory ──────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## TaskFlow API

A secure, scalable REST API with JWT authentication and role-based access control.

### Features
- 🔐 **JWT Authentication** — Access + Refresh token flow
- 👥 **Role-Based Access** — `user` and `admin` roles
- ✅ **Task Management** — Full CRUD with status/priority tracking
- 🛡️ **Security** — bcrypt password hashing, input validation, rate limiting
- 📄 **Pagination** — All list endpoints support page/page_size
- 🔍 **Search & Filter** — Filter tasks by status, priority, search query

### Authentication
Use the `/api/v1/auth/login` endpoint to get a JWT token, then pass it as:
```
Authorization: Bearer <your_token>
```
        """,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        lifespan=lifespan,
    )

    # ── Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging
    register_middleware(app)

    # ── Exception handlers
    register_exception_handlers(app)

    # ── Routes
    app.include_router(api_router)

    # ── Health check
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            environment=settings.environment,
            database="connected",
        )

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/api/v1/docs",
            "health": "/health",
        }

    return app


app = create_app()
