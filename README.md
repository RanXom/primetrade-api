# TaskFlow API

A production-ready, secure, and scalable REST API built with **FastAPI** + **PostgreSQL**, featuring JWT authentication, role-based access control (RBAC), and a React frontend test UI.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [API Documentation](#api-documentation)
- [Authentication Flow](#authentication-flow)
- [Role-Based Access](#role-based-access)
- [Running Tests](#running-tests)
- [Docker Deployment](#docker-deployment)
- [Scalability Notes](#scalability-notes)

---

## Tech Stack

| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Framework    | FastAPI 0.111                           |
| Language     | Python 3.11.14                          |
| Database     | PostgreSQL 16 (via asyncpg + SQLAlchemy 2) |
| Auth         | JWT (python-jose) + bcrypt (passlib)    |
| Migrations   | Alembic                                 |
| Validation   | Pydantic v2                             |
| Rate Limiting| SlowAPI                                 |
| Caching      | Redis (optional)                        |
| Logging      | Loguru                                  |
| Testing      | Pytest + pytest-asyncio + HTTPX         |
| Deployment   | Docker + Docker Compose + Nginx         |

---

## Project Structure

```
taskflow-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── deps.py            # Auth dependencies (JWT guards, role checks)
│   │       ├── router.py          # Aggregates all v1 routes
│   │       └── endpoints/
│   │           ├── auth.py        # /auth/* — register, login, refresh, me
│   │           ├── tasks.py       # /tasks/* — CRUD + filters
│   │           └── admin.py       # /admin/* — user management
│   ├── core/
│   │   ├── config.py              # Pydantic settings (reads .env)
│   │   ├── security.py            # JWT creation/validation, password hashing
│   │   └── logging.py             # Loguru setup
│   ├── db/
│   │   └── session.py             # Async SQLAlchemy engine + session factory
│   ├── middleware/
│   │   ├── exception_handler.py   # Global error handlers
│   │   └── logging.py             # Request/response logging middleware
│   ├── models/
│   │   ├── user.py                # User ORM model
│   │   └── task.py                # Task ORM model
│   ├── schemas/
│   │   ├── user.py                # Request/response Pydantic schemas
│   │   ├── task.py                # Task schemas
│   │   └── common.py              # APIResponse, ErrorResponse wrappers
│   ├── services/
│   │   ├── user_service.py        # User business logic (queries + mutations)
│   │   └── task_service.py        # Task business logic
│   └── main.py                    # App factory, lifespan, middleware setup
├── alembic/                       # Database migrations
├── scripts/
│   └── seed.py                    # Creates initial admin user
├── tests/
│   └── test_api.py                # Integration tests
├── taskflow-frontend/
│   └── index.html                 # Single-file React UI for API testing
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Quick Start

### Prerequisites

- Python 3.11.14 (Note: `pip install -r requirements.txt` does not work with Python 3.12)
- PostgreSQL 16+
- Redis (optional, for caching)

### 1. Clone and install

```bash
git clone https://github.com/RanXom/taskflow-api.git
cd taskflow-api

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum
```

### 3. Initialize the database

```bash
# Tables are auto-created on startup via SQLAlchemy
# Or run Alembic migrations (recommended for production):
alembic upgrade head

# Seed the initial admin user
python scripts/seed.py
```

### 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open the frontend

Open `taskflow-frontend/index.html` in your browser. It connects to `http://localhost:8000` by default.

Default admin credentials:
- **Email:** `admin@taskflow.dev`
- **Password:** `Admin1234!`

---

## Environment Variables

| Variable                      | Default                        | Description                          |
|-------------------------------|--------------------------------|--------------------------------------|
| `DATABASE_URL`                | postgresql+asyncpg://...       | Async PostgreSQL connection string   |
| `SECRET_KEY`                  | *(required)*                   | JWT signing key (min 32 chars)       |
| `ALGORITHM`                   | `HS256`                        | JWT signing algorithm                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                           | Access token TTL in minutes          |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                            | Refresh token TTL in days            |
| `ALLOWED_ORIGINS`             | `http://localhost:3000,...`    | Comma-separated CORS origins         |
| `BCRYPT_ROUNDS`               | `12`                           | bcrypt work factor                   |
| `REDIS_URL`                   | `redis://localhost:6379/0`     | Redis URL for caching                |
| `DEBUG`                       | `false`                        | Enable debug mode                    |
| `ENVIRONMENT`                 | `production`                   | Environment label                    |

---

## Database Setup

### Schema Overview

```sql
-- users table
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    username    VARCHAR(50)  UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name   VARCHAR(100),
    role        user_role NOT NULL DEFAULT 'user',   -- ENUM: user | admin
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login  TIMESTAMPTZ
);

-- tasks table
CREATE TABLE tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      task_status NOT NULL DEFAULT 'todo',       -- ENUM: todo | in_progress | done | cancelled
    priority    task_priority NOT NULL DEFAULT 'medium',   -- ENUM: low | medium | high | urgent
    is_public   BOOLEAN NOT NULL DEFAULT FALSE,
    due_date    TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
```

### Alembic Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## API Documentation

Interactive docs are auto-generated by FastAPI:

| Format   | URL                              |
|----------|----------------------------------|
| Swagger  | http://localhost:8000/api/v1/docs  |
| ReDoc    | http://localhost:8000/api/v1/redoc |
| OpenAPI  | http://localhost:8000/api/v1/openapi.json |

### Endpoint Reference

#### Authentication — `/api/v1/auth`

| Method | Path                  | Auth | Description                          |
|--------|-----------------------|------|--------------------------------------|
| POST   | `/auth/register`      | None | Create a new user account            |
| POST   | `/auth/login`         | None | Login and receive JWT tokens         |
| POST   | `/auth/refresh`       | None | Exchange refresh token for new tokens|
| GET    | `/auth/me`            | User | Get current user's profile           |
| PUT    | `/auth/me/password`   | User | Change current user's password       |

#### Tasks — `/api/v1/tasks`

| Method | Path                  | Auth  | Description                          |
|--------|-----------------------|-------|--------------------------------------|
| GET    | `/tasks`              | User  | List current user's tasks (paginated)|
| POST   | `/tasks`              | User  | Create a new task                    |
| GET    | `/tasks/public`       | None  | List all public tasks                |
| GET    | `/tasks/{id}`         | Opt.  | Get task by ID (public or owned)     |
| PATCH  | `/tasks/{id}`         | User  | Update a task (own or admin)         |
| DELETE | `/tasks/{id}`         | User  | Delete a task (own or admin)         |
| GET    | `/tasks/admin/all`    | Admin | List ALL tasks across all users      |

#### Admin — `/api/v1/admin`

| Method | Path                  | Auth  | Description                          |
|--------|-----------------------|-------|--------------------------------------|
| GET    | `/admin/users`        | Admin | List all users (paginated)           |
| GET    | `/admin/users/{id}`   | Admin | Get any user by ID                   |
| PATCH  | `/admin/users/{id}`   | Admin | Update user role / active status     |
| DELETE | `/admin/users/{id}`   | Admin | Delete a user and all their data     |

#### Health — `/health`

Returns `{ status, version, environment, database }`.

### Request/Response Format

All endpoints return a consistent envelope:

```json
// Success
{
  "success": true,
  "message": "OK",
  "data": { ... }
}

// Error
{
  "success": false,
  "message": "Validation failed",
  "errors": [{ "field": "password", "message": "..." }],
  "error_code": "VALIDATION_ERROR"
}
```

---

## Authentication Flow

```
1. POST /auth/register  →  { user }
2. POST /auth/login     →  { access_token, refresh_token, expires_in }
3. GET  /auth/me        →  Authorization: Bearer <access_token>
4. POST /auth/refresh   →  { refresh_token }  →  new tokens
```

**Token structure (JWT payload):**
```json
{
  "sub": "user-uuid",
  "role": "user",
  "username": "johndoe",
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access"
}
```

---

## Role-Based Access

| Capability                     | user | admin |
|-------------------------------|------|-------|
| Register / Login               | ✅   | ✅    |
| View own tasks                 | ✅   | ✅    |
| Create / edit / delete own tasks| ✅  | ✅    |
| View public tasks              | ✅   | ✅    |
| Edit / delete any task         | ✗    | ✅    |
| View all tasks (admin/all)     | ✗    | ✅    |
| List all users                 | ✗    | ✅    |
| Promote/demote users           | ✗    | ✅    |
| Activate/deactivate accounts   | ✗    | ✅    |
| Delete any user                | ✗    | ✅    |

---

## Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite-compatible setup via HTTPX AsyncClient and ASGITransport — no live database required for unit tests.

---

## Docker Deployment

### Build and run the full stack

```bash
# Copy and configure environment
cp .env.example .env

# Build and start all services
docker compose up --build -d

# Seed initial admin
docker compose exec api python scripts/seed.py

# View logs
docker compose logs -f api
```

### Services

| Service    | Port  | Description              |
|------------|-------|--------------------------|
| `api`      | 8000  | FastAPI application      |
| `postgres` | 5432  | PostgreSQL database      |
| `redis`    | 6379  | Redis cache              |
| `frontend` | 3000  | Nginx serving the UI     |

---

## Scalability Notes

### Current Architecture

```
Client → Nginx (reverse proxy) → FastAPI (multiple workers) → PostgreSQL + Redis
```

### Horizontal Scaling

- **Multiple API workers:** `uvicorn app.main:app --workers 4` — stateless design enables N workers behind a load balancer
- **Connection pooling:** SQLAlchemy async engine with `pool_size=10, max_overflow=20` — handles high concurrency
- **Stateless JWT:** No server-side session state — tokens are self-contained, works across any number of nodes

### Caching Layer (Redis)

The `redis` dependency is installed and configured. Extend with:
- **Response caching** — cache expensive list queries with TTL
- **Rate limit counters** — distributed rate limiting across instances
- **Token blacklist** — revoke JWTs on logout (optional enhancement)

### Load Balancing

Deploy behind Nginx or AWS ALB:

```nginx
upstream taskflow {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}
```

### Microservices Path

The modular structure (`services/`, `models/`, `api/v1/endpoints/`) is designed for extraction. To scale to microservices:

1. **Auth Service** — extract `auth.py` + `user_service.py` → standalone JWT-issuing service
2. **Task Service** — extract `tasks.py` + `task_service.py` → dedicated CRUD service
3. **API Gateway** — route via Kong, Traefik, or AWS API Gateway
4. **Message Queue** — add Celery + Redis/RabbitMQ for async task processing (email notifications, webhooks)

### Database Scaling

- **Read replicas:** Point read-heavy queries to replicas using SQLAlchemy's `execution_options`
- **Partitioning:** Partition `tasks` table by `created_at` for large datasets
- **Indexing:** Key indexes already defined on `email`, `username`, `owner_id`, `status`, `priority`

### Observability

- **Logging:** Structured JSON logs via Loguru → ship to ELK or Datadog
- **Metrics:** Add `prometheus-fastapi-instrumentator` for Prometheus scraping
- **Tracing:** Add `opentelemetry-instrumentation-fastapi` for distributed tracing

### Security Hardening (Production Checklist)

- [ ] Rotate `SECRET_KEY` and store in AWS Secrets Manager / HashiCorp Vault
- [ ] Enable HTTPS via Let's Encrypt / AWS ACM
- [ ] Set `BCRYPT_ROUNDS=14` for stronger password hashing
- [ ] Configure `ALLOWED_ORIGINS` to exact production domains only
- [ ] Enable Redis-backed token blacklist for logout invalidation
- [ ] Add IP-based rate limiting per user/endpoint
- [ ] Enable PostgreSQL SSL (`sslmode=require`)
- [ ] Set up automated DB backups
