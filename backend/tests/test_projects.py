import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.project import Project

# Setup an isolated in-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
def client(db_session):
    """Override get_db with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Create a sample user in the test database."""
    user = User(
        id=uuid.uuid4(),
        email="tester@example.com",
        hashed_password="hashed_secure_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_project_success(client, sample_user):
    """Verify POST /api/v1/projects creates a project and returns 201."""
    payload = {
        "name": "Design Mobile App",
        "description": "Figma mockups and user flows",
        "user_id": str(sample_user.id),
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Design Mobile App"
    assert data["description"] == "Figma mockups and user flows"
    assert data["user_id"] == str(sample_user.id)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_project_validation_error(client, sample_user):
    """Verify POST /api/v1/projects returns 422 when name is empty."""
    payload = {
        "name": "",  # Violates min_length=1
        "description": "Valid description",
        "user_id": str(sample_user.id),
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 422


def test_create_project_user_not_found(client):
    """Verify POST /api/v1/projects returns 400 when user_id does not exist."""
    random_user_id = str(uuid.uuid4())
    payload = {
        "name": "Orphan Project",
        "user_id": random_user_id,
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_list_projects_pagination(client, sample_user, db_session):
    """Verify GET /api/v1/projects returns paginated envelope and accurate count."""
    for i in range(5):
        proj = Project(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            name=f"Project {i+1}",
            description=f"Desc {i+1}",
        )
        db_session.add(proj)
    db_session.commit()

    # Request first page of 2 items
    response = client.get("/api/v1/projects?limit=2&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2

    # Request second page of 2 items
    response_p2 = client.get("/api/v1/projects?limit=2&offset=2")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert len(data_p2["items"]) == 2

    # Request third page of 2 items (only 1 item remaining)
    response_p3 = client.get("/api/v1/projects?limit=2&offset=4")
    assert response_p3.status_code == 200
    data_p3 = response_p3.json()
    assert len(data_p3["items"]) == 1


def test_update_project_success(client, sample_user, db_session):
    """Verify PATCH /api/v1/projects/{id} partially updates fields and returns 200."""
    project = Project(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Old Name",
        description="Old Description",
    )
    db_session.add(project)
    db_session.commit()

    # Update only the name
    update_payload = {"name": "New Renovated Name"}
    response = client.patch(f"/api/v1/projects/{project.id}", json=update_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "New Renovated Name"
    assert data["description"] == "Old Description"


def test_update_project_not_found(client):
    """Verify PATCH /api/v1/projects/{id} returns 404 when ID is missing."""
    random_id = str(uuid.uuid4())
    response = client.patch(f"/api/v1/projects/{random_id}", json={"name": "Ghost Project"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
