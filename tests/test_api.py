"""
Integration tests for TaskFlow API.

Run with:
    pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import Base, engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def user_data():
    return {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "Testpass1",
        "full_name": "Test User",
    }


# ─── Auth Tests ───────────────────────────────────────────────────────────────

class TestAuth:
    async def test_register_success(self, client, user_data):
        resp = await client.post("/api/v1/auth/register", json=user_data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["email"] == user_data["email"]
        assert body["data"]["role"] == "user"

    async def test_register_duplicate_email(self, client, user_data):
        await client.post("/api/v1/auth/register", json=user_data)
        resp = await client.post("/api/v1/auth/register", json=user_data)
        assert resp.status_code == 409

    async def test_register_weak_password(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "weakpass",
        })
        assert resp.status_code == 422

    async def test_login_success(self, client, user_data):
        await client.post("/api/v1/auth/register", json=user_data)
        resp = await client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    async def test_login_wrong_password(self, client, user_data):
        await client.post("/api/v1/auth/register", json=user_data)
        resp = await client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    async def test_get_me_authenticated(self, client, user_data):
        await client.post("/api/v1/auth/register", json=user_data)
        login = await client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"],
        })
        token = login.json()["data"]["access_token"]
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == user_data["email"]

    async def test_get_me_unauthenticated(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ─── Task Tests ───────────────────────────────────────────────────────────────

class TestTasks:
    @pytest_asyncio.fixture
    async def auth_headers(self, client):
        reg_data = {
            "email": "taskuser@example.com",
            "username": "taskuser",
            "password": "Taskpass1",
        }
        await client.post("/api/v1/auth/register", json=reg_data)
        login = await client.post("/api/v1/auth/login", json={
            "email": reg_data["email"],
            "password": reg_data["password"],
        })
        token = login.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_create_task(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "My first task", "priority": "high"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["title"] == "My first task"

    async def test_list_tasks(self, client, auth_headers):
        await client.post("/api/v1/tasks", json={"title": "Task 1"}, headers=auth_headers)
        resp = await client.get("/api/v1/tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] >= 1

    async def test_update_task(self, client, auth_headers):
        create = await client.post(
            "/api/v1/tasks",
            json={"title": "Old title"},
            headers=auth_headers,
        )
        task_id = create.json()["data"]["id"]
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Updated title", "status": "in_progress"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated title"

    async def test_delete_task(self, client, auth_headers):
        create = await client.post(
            "/api/v1/tasks",
            json={"title": "To delete"},
            headers=auth_headers,
        )
        task_id = create.json()["data"]["id"]
        resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_create_task_unauthenticated(self, client):
        resp = await client.post("/api/v1/tasks", json={"title": "Test"})
        assert resp.status_code == 401
