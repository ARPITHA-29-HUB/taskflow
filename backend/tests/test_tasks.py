import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.cache import get_cache, CacheService
from app.models.user import User
from app.models.project import Project
from app.models.task import Task


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
        # Verify arguments: task_id, title, due_date
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
        # Should not trigger reminder
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

    # Verify cache key was purged upon task creation
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
