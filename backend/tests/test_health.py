from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_status_code():
    """Verify that the health check endpoint returns HTTP 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload():
    """Verify that the health check returns expected status in JSON."""
    response = client.get("/health")
    data = response.json()
    assert data.get("status") == "ok"
    assert "version" in data


def test_root_endpoint():
    """Verify that the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "TaskFlow" in data["message"]
