"""
Unit and Integration Tests for Observability, Settings, and Readiness
---------------------------------------------------------------------
Verifies:
1. /health liveness probe returns 200 and metadata
2. /ready readiness probe returns 200 when database is operational
3. /ready readiness probe returns 503 Service Unavailable on database failure
4. Request-ID generation when missing
5. Request-ID preservation when supplied by client
6. Pydantic Settings configuration and helper parsing
7. Structured JSON log formatting
"""

import json
import logging
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.database import get_db
from app.main import app
from app.middleware import JSONLogFormatter


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_probe_returns_200_and_request_id(client):
    """Verify /health returns 200 OK, environment metadata, and attaches X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "service" in data

    # Verify X-Request-ID response header
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    # Check that it is a valid UUID
    uuid_obj = uuid.UUID(req_id)
    assert str(uuid_obj) == req_id


def test_readiness_probe_healthy(client):
    """Verify /ready probe returns 200 OK and reports connected database."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "X-Request-ID" in response.headers


def test_readiness_probe_database_failure(client):
    """Verify /ready probe returns 503 Service Unavailable when the database fails."""

    def broken_db():
        mock_session = MagicMock()
        mock_session.execute.side_effect = OperationalError("connection refused", {}, None)
        yield mock_session

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["database"] == "disconnected"
        assert "Database connection failed" in data["detail"]
        assert "X-Request-ID" in response.headers
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_incoming_request_id_preserved(client):
    """Verify that a client-provided X-Request-ID is honored and returned."""
    custom_id = "trace-client-abc-9876"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_pydantic_settings_parsing():
    """Verify Pydantic Settings class validates defaults and properties."""
    custom_settings = Settings(
        APP_NAME="CustomTaskFlow",
        CORS_ORIGINS="http://site-a.com, http://site-b.com",
        TRUSTED_PROXIES="10.0.0.1, 10.0.0.2",
    )
    assert custom_settings.APP_NAME == "CustomTaskFlow"
    assert custom_settings.cors_origins_list == ["http://site-a.com", "http://site-b.com"]
    assert custom_settings.trusted_proxies_set == {"10.0.0.1", "10.0.0.2"}


def test_structured_json_log_formatter():
    """Verify JSONLogFormatter creates valid JSON with required observability fields."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="taskflow.test",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test event processed successfully",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    record.http_method = "POST"
    record.path = "/api/v1/tasks"
    record.status_code = 201
    record.duration_ms = 18.5

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test event processed successfully"
    assert parsed["request_id"] == "req-12345"
    assert parsed["method"] == "POST"
    assert parsed["path"] == "/api/v1/tasks"
    assert parsed["status_code"] == 201
    assert parsed["duration_ms"] == 18.5
    assert "timestamp" in parsed


def test_sensitive_fields_never_logged_in_plaintext():
    """Verify that sensitive fields (passwords, tokens) are never emitted in plain text."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="taskflow.auth",
        level=logging.INFO,
        pathname="auth.py",
        lineno=10,
        msg="User authenticated",
        args=(),
        exc_info=None,
    )
    # Simulate an accidental injection of a password attribute
    record.password = "SuperSecretPassword123!"
    record.access_token = "eyJhbGciOiJIUzI1NiIsIn..."

    formatted = formatter.format(record)
    assert "SuperSecretPassword123!" not in formatted
    assert "eyJhbGciOiJIUzI1NiIsIn..." not in formatted
