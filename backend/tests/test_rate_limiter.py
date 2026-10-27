import uuid

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
from app.rate_limiter import RateLimiterService, get_rate_limiter

# Isolated in-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DummyCache:
    """Mock cache to prevent real Redis calls during testing."""

    def get(self, key: str):
        return None

    def set(self, key: str, value, ttl: int = 60):
        return True

    def delete(self, key: str):
        return True

    def invalidate_project_summary(self, project_id):
        return True


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
def test_rate_limiter():
    """Create a fresh isolated RateLimiterService (in-memory mode for tests)."""
    limiter = RateLimiterService(enable_redis=False, capacity=30.0, refill_rate=0.5)
    limiter.in_memory.reset()
    return limiter


@pytest.fixture(scope="function")
def client(db_session, test_rate_limiter):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_cache():
        return DummyCache()

    def override_get_rate_limiter():
        return test_rate_limiter

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache
    app.dependency_overrides[get_rate_limiter] = override_get_rate_limiter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="ratelimit_user@example.com",
        hashed_password="hashed_secure_pass",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_project(db_session, sample_user):
    project = Project(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Rate Limit Project",
        description="Testing rate limiting",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_rate_limiter_allows_30_requests_and_blocks_31st(client, sample_user, sample_project):
    """Test that a client can make up to 30 requests, and the 31st request is blocked with HTTP 429 and Retry-After."""
    payload = {
        "title": "Rate Limited Task",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
    }

    # 1. First 30 requests should all be allowed (HTTP 201)
    for i in range(1, 31):
        res = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "198.51.100.1"})
        assert res.status_code == 201, f"Request {i} unexpectedly failed: {res.text}"

    # 2. 31st request should be rejected with 429 Too Many Requests
    blocked_res = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "198.51.100.1"})
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers
    retry_after = int(blocked_res.headers["Retry-After"])
    assert retry_after >= 1
    assert "Rate limit exceeded" in blocked_res.json()["detail"]


def test_rate_limiter_client_isolation(client, sample_user, sample_project):
    """Test that exhausting the rate limit for Client A does not block Client B."""
    payload = {
        "title": "Isolation Task",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
    }

    # Client A consumes all 30 tokens
    for _ in range(30):
        res = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "203.0.113.10"})
        assert res.status_code == 201

    # Client A is now blocked
    res_a_blocked = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "203.0.113.10"})
    assert res_a_blocked.status_code == 429

    # Client B should still have their full bucket and be allowed
    res_b = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "203.0.113.20"})
    assert res_b.status_code == 201


def test_rate_limiter_nested_project_route(client, sample_user, sample_project):
    """Test that the nested route POST /api/v1/projects/{id}/tasks is also protected by the rate limiter."""
    payload = {
        "title": "Nested Route Task",
        "user_id": str(sample_user.id),
    }

    url = f"/api/v1/projects/{sample_project.id}/tasks"

    for i in range(1, 31):
        res = client.post(url, json=payload, headers={"X-Forwarded-For": "192.0.2.55"})
        assert res.status_code == 201

    blocked_res = client.post(url, json=payload, headers={"X-Forwarded-For": "192.0.2.55"})
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers


def test_rate_limiter_spoofed_proxy_header_protection(client, sample_user, sample_project, monkeypatch):
    """Test that when requests come from an untrusted client, spoofed X-Forwarded-For headers are ignored."""
    # Configure only 127.0.0.1 as trusted proxy, not 'testclient'
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1")

    payload = {
        "title": "Spoof Test Task",
        "user_id": str(sample_user.id),
        "project_id": str(sample_project.id),
    }

    # An attacker rotates X-Forwarded-For on every request, but their direct connection is untrusted
    for i in range(30):
        res = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": f"10.0.0.{i + 1}"})
        assert res.status_code == 201

    # The 31st request with yet another spoofed IP is STILL blocked because the direct host was throttled
    blocked = client.post("/api/v1/tasks", json=payload, headers={"X-Forwarded-For": "10.0.0.99"})
    assert blocked.status_code == 429
