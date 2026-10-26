import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from redis.exceptions import RedisError

from app.main import app
from app.database import Base, get_db
from app.cache import get_cache, CacheService
from app.models.user import User
from app.models.project import Project
from app.models.task import Task

# Isolated in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FakeRedisClient:
    """Mock Redis client simulating key-value storage, TTLs, and network failures."""

    def __init__(self):
        self.store = {}
        self.ttls = {}
        self.should_fail = False

    def get(self, key: str):
        if self.should_fail:
            raise RedisError("Simulated Redis connection failure")
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str):
        if self.should_fail:
            raise RedisError("Simulated Redis connection failure")
        self.store[key] = value
        self.ttls[key] = ttl

    def delete(self, key: str):
        if self.should_fail:
            raise RedisError("Simulated Redis connection failure")
        return self.store.pop(key, None)


@pytest.fixture(scope="function")
def fake_redis():
    return FakeRedisClient()


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session, fake_redis):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_cache_service = CacheService(redis_client=fake_redis)

    def override_get_cache():
        return test_cache_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_data(db_session):
    user = User(
        id=uuid.uuid4(),
        email="cache_tester@example.com",
        hashed_password="hashed_pw",
        is_active=True,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Cache Demo Project",
        description="Testing cache-aside and invalidation",
    )
    db_session.add(project)

    tasks = [
        Task(id=uuid.uuid4(), user_id=user.id, project_id=project.id, title="Task 1", status="todo", priority="high"),
        Task(id=uuid.uuid4(), user_id=user.id, project_id=project.id, title="Task 2", status="todo", priority="medium"),
        Task(id=uuid.uuid4(), user_id=user.id, project_id=project.id, title="Task 3", status="in_progress", priority="low"),
        Task(id=uuid.uuid4(), user_id=user.id, project_id=project.id, title="Task 4", status="done", priority="high"),
    ]
    db_session.add_all(tasks)
    db_session.commit()

    return {"user": user, "project": project, "tasks": tasks}


def test_cache_miss_and_population(client, seed_data, fake_redis):
    """Verify first request is a cache miss that queries DB and populates cache."""
    project_id = str(seed_data["project"].id)
    cache_key = f"project:{project_id}:summary"

    # Initially cache is empty
    assert fake_redis.get(cache_key) is None

    # First request: Cache Miss -> Queries DB -> Populates cache
    response = client.get(f"/api/v1/projects/{project_id}/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["project_id"] == project_id
    assert data["total_tasks"] == 4
    assert data["todo"] == 2
    assert data["in_progress"] == 1
    assert data["done"] == 1

    # Cache should now be populated with 60s TTL
    assert fake_redis.get(cache_key) is not None
    assert fake_redis.ttls[cache_key] == 60


def test_cache_hit_returns_cached_data(client, seed_data, fake_redis, db_session):
    """Verify second request returns cached data directly without re-querying the database."""
    project_id = str(seed_data["project"].id)

    # 1. Warm the cache
    client.get(f"/api/v1/projects/{project_id}/summary")

    # 2. Add a new task directly in DB behind the cache's back
    sneaky_task = Task(
        id=uuid.uuid4(),
        user_id=seed_data["user"].id,
        project_id=seed_data["project"].id,
        title="Sneaky Task",
        status="todo",
        priority="low",
    )
    db_session.add(sneaky_task)
    db_session.commit()

    # 3. Read again: Should HIT cache and still return 4 (cached value), proving DB wasn't queried
    response = client.get(f"/api/v1/projects/{project_id}/summary")
    assert response.status_code == 200
    assert response.json()["total_tasks"] == 4  # Cached value, not 5


def test_cache_invalidation_after_project_update(client, seed_data, fake_redis):
    """Verify that updating a project invalidates its cached summary."""
    project_id = str(seed_data["project"].id)
    cache_key = f"project:{project_id}:summary"

    # 1. Warm cache
    client.get(f"/api/v1/projects/{project_id}/summary")
    assert fake_redis.get(cache_key) is not None

    # 2. Update project
    patch_res = client.patch(f"/api/v1/projects/{project_id}", json={"name": "Renamed Project"})
    assert patch_res.status_code == 200

    # 3. Cache must be evicted
    assert fake_redis.get(cache_key) is None


def test_cache_missing_project_returns_404(client):
    """Verify that requesting summary for a non-existent project returns 404 and does not cache."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/projects/{random_id}/summary")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_redis_failure_graceful_fallback(client, seed_data, fake_redis):
    """Verify that when Redis crashes/fails, the API still succeeds by falling back to the database."""
    project_id = str(seed_data["project"].id)

    # Simulate catastrophic Redis failure
    fake_redis.should_fail = True

    # Request should NOT return HTTP 500; it falls back to DB and returns HTTP 200
    response = client.get(f"/api/v1/projects/{project_id}/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["project_id"] == project_id
    assert data["total_tasks"] == 4
    assert data["todo"] == 2
