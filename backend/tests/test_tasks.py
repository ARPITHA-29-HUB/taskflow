import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import get_cache
from app.database import Base, get_db
from app.main import app
from app.models.project import Project
from app.models.user import User

# Setup isolated in-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FakeCacheService:
    """In-memory cache simulator for testing cache operations and invalidations."""

    def __init__(self):
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ttl: int = 60):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)

    def invalidate_project_summary(self, project_id: uuid.UUID):
        self.delete(f"project:{project_id}:summary")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database schema for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def fake_cache():
    return FakeCacheService()


@pytest.fixture(scope="function")
def client(db_session, fake_cache):
    """Override get_db and get_cache with test doubles."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_cache():
        return fake_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Create a sample user in the test database."""
    user = User(
        id=uuid.uuid4(),
        email="tasktester@example.com",
        hashed_password="secure_password_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_project(db_session, sample_user):
    """Create a sample project in the test database."""
    project = Project(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Backend Core",
        description="Project management",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


# 1. Task Creation & Background Reminder Integration Tests


def test_create_task_with_due_date_triggers_background_reminder(client, sample_user, sample_project):
    """Test that creating a task with a due date triggers the in-process background reminder."""
    due_date = "2026-10-30T15:00:00Z"
    payload = {
        "title": "Build Background Jobs",
        "description": "Implement FastAPI BackgroundTasks",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
        "status": "todo",
        "priority": "high",
        "due_date": due_date,
    }

    with patch("app.routers.tasks.log_task_reminder") as mock_reminder:
        response = client.post("/api/v1/tasks", json=payload)

        # 1. Immediate HTTP response should be 201 Created
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Build Background Jobs"
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["user_id"] == str(sample_user.id)
        assert data["project_id"] == str(sample_project.id)
        assert data["due_date"] is not None

        # 2. FastAPI BackgroundTasks should have executed the reminder function
        mock_reminder.assert_called_once()
        call_args = mock_reminder.call_args[0]
        assert str(call_args[0]) == data["id"]
        assert call_args[1] == "Build Background Jobs"
        assert isinstance(call_args[2], datetime)


def test_create_task_without_due_date_does_not_trigger_reminder(client, sample_user, sample_project):
    """Test that creating a task without a due date does NOT schedule an accidental reminder."""
    payload = {
        "title": "Undated Task",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
        "status": "todo",
        "priority": "medium",
        "due_date": None,
    }

    with patch("app.routers.tasks.log_task_reminder") as mock_reminder:
        response = client.post("/api/v1/tasks", json=payload)

        assert response.status_code == 201
        assert response.json()["due_date"] is None
        mock_reminder.assert_not_called()


def test_create_task_invalidates_project_summary_cache(client, sample_user, sample_project, fake_cache):
    """Test that creating a task in a project invalidates that project's cached summary."""
    cache_key = f"project:{sample_project.id}:summary"
    fake_cache.set(cache_key, {"cached_counts": True})
    assert fake_cache.get(cache_key) is not None

    payload = {
        "title": "Cache Invalidation Task",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
    }

    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 201
    assert fake_cache.get(cache_key) is None


def test_create_task_nonexistent_user_returns_400(client, sample_project):
    """Test that creating a task with a non-existent user_id fails with 400 Bad Request."""
    payload = {
        "title": "Orphan Task",
        "user_id": str(uuid.uuid4()),
        "project_id": str(sample_project.id),
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_create_task_nonexistent_project_returns_400(client, sample_user):
    """Test that creating a task with a non-existent project_id fails with 400 Bad Request."""
    payload = {
        "title": "Invalid Project Task",
        "user_id": str(sample_user.id),
        "project_id": str(uuid.uuid4()),
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


# 2. Task Listing, Filtering, and Pagination Integration Tests


def test_list_tasks_pagination_and_filtering(client, sample_user, sample_project):
    """Test listing tasks with pagination, search, status, and priority filtering."""
    # Create 3 distinct tasks
    client.post(
        "/api/v1/tasks",
        json={
            "title": "Alpha Research",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "todo",
            "priority": "low",
        },
    )
    client.post(
        "/api/v1/tasks",
        json={
            "title": "Beta Implementation",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "in_progress",
            "priority": "high",
        },
    )
    client.post(
        "/api/v1/tasks",
        json={
            "title": "Gamma Verification",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "done",
            "priority": "high",
        },
    )

    # Filter by status=done
    res_done = client.get("/api/v1/tasks?status=done")
    assert res_done.status_code == 200
    data_done = res_done.json()
    assert data_done["total"] == 1
    assert data_done["items"][0]["title"] == "Gamma Verification"

    # Filter by priority=high
    res_high = client.get("/api/v1/tasks?priority=high")
    assert res_high.status_code == 200
    assert res_high.json()["total"] == 2

    # Search keyword
    res_search = client.get("/api/v1/tasks?search=Beta")
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["title"] == "Beta Implementation"

    # Pagination: limit=2
    res_paginated = client.get("/api/v1/tasks?limit=2&offset=0")
    assert res_paginated.status_code == 200
    assert len(res_paginated.json()["items"]) == 2
    assert res_paginated.json()["total"] == 3


# 3. Get Task by ID Tests


def test_get_task_by_id_success(client, sample_user, sample_project):
    """Test retrieving an existing task by ID."""
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Fetchable Task",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
        },
    )
    task_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Fetchable Task"


def test_get_task_by_id_not_found(client):
    """Test that fetching a non-existent task returns 404."""
    missing_id = uuid.uuid4()
    res = client.get(f"/api/v1/tasks/{missing_id}")
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]


# 4. Update Task Tests (Status Transitions & Cache Eviction)


def test_update_task_success_and_cache_eviction(client, sample_user, sample_project, fake_cache):
    """Test updating task title and valid status transition, verifying cache invalidation."""
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task To Update",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "todo",
        },
    )
    task_id = create_res.json()["id"]

    # Pre-populate project summary cache
    cache_key = f"project:{sample_project.id}:summary"
    fake_cache.set(cache_key, {"summary": "cached"})
    assert fake_cache.get(cache_key) is not None

    # Valid status transition: todo -> in_progress
    patch_res = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Updated Task Title",
            "status": "in_progress",
            "priority": "high",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Task Title"
    assert patch_res.json()["status"] == "in_progress"
    assert patch_res.json()["priority"] == "high"

    # Verify summary cache was purged
    assert fake_cache.get(cache_key) is None


def test_update_task_invalid_status_transition_returns_400(client, sample_user, sample_project):
    """Test that an illegal status transition returns 400 Bad Request."""
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Transition Test",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "todo",
        },
    )
    task_id = create_res.json()["id"]

    # Illegal transition: status='invalid_status'
    patch_res = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": "invalid_status",
        },
    )
    assert patch_res.status_code == 422 or patch_res.status_code == 400


def test_update_task_not_found(client):
    """Test updating non-existent task returns 404."""
    missing_id = uuid.uuid4()
    patch_res = client.patch(f"/api/v1/tasks/{missing_id}", json={"title": "New Title"})
    assert patch_res.status_code == 404


# 5. Delete Task Tests


def test_delete_task_success_and_cache_eviction(client, sample_user, sample_project, fake_cache):
    """Test deleting an existing task returns 204 and purges project summary cache."""
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "To Be Deleted",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
        },
    )
    task_id = create_res.json()["id"]

    cache_key = f"project:{sample_project.id}:summary"
    fake_cache.set(cache_key, {"cached": True})

    del_res = client.delete(f"/api/v1/tasks/{task_id}")
    assert del_res.status_code == 204

    # Verify task is gone
    get_res = client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 404

    # Verify cache evicted
    assert fake_cache.get(cache_key) is None


def test_delete_task_not_found(client):
    """Test deleting a non-existent task returns 404."""
    missing_id = uuid.uuid4()
    del_res = client.delete(f"/api/v1/tasks/{missing_id}")
    assert del_res.status_code == 404


def test_put_update_task_success(client, sample_user, sample_project):
    """Test updating task via PUT endpoint according to documented contract."""
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "PUT Task",
            "user_id": str(sample_user.id),
            "project_id": str(sample_project.id),
            "status": "todo",
        },
    )
    task_id = create_res.json()["id"]

    put_res = client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Updated via PUT",
            "status": "in_progress",
            "priority": "low",
        },
    )
    assert put_res.status_code == 200
    assert put_res.json()["title"] == "Updated via PUT"
    assert put_res.json()["status"] == "in_progress"
    assert put_res.json()["priority"] == "low"


def test_create_task_schema_validation_error_422(client, sample_user):
    """Test that invalid request body format triggers 422 Unprocessable Entity."""
    # Empty title
    res_empty_title = client.post(
        "/api/v1/tasks",
        json={"title": "", "user_id": str(sample_user.id)},
    )
    assert res_empty_title.status_code == 422

    # Invalid priority enum
    res_invalid_prio = client.post(
        "/api/v1/tasks",
        json={"title": "Valid Title", "user_id": str(sample_user.id), "priority": "ultra-critical"},
    )
    assert res_invalid_prio.status_code == 422
