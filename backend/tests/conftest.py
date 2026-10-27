"""
Pytest Global Configuration & Safety Guard Fixtures
---------------------------------------------------
Configures:
- Test database connection via environment variables (TEST_DATABASE_URL).
- Safety guard: prevents accidental test connection to production databases.
- Isolated in-memory SQLite fallback when no external test database is provided.
- PostgreSQL compatibility testing fixtures.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


def get_test_database_url() -> str:
    """Resolve test database URL, strictly enforcing non-production safety rules."""
    test_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    # Safety Guard: Never permit running tests against production targets
    app_env = os.getenv("APP_ENV", "testing").lower()
    if app_env == "production":
        raise RuntimeError("SAFETY GUARD TRIGGERED: Tests cannot execute under APP_ENV=production!")

    # Check for obvious production database names
    lower_url = test_url.lower()
    if "prod" in lower_url or ("taskflow" in lower_url and "test" not in lower_url and "sqlite" not in lower_url):
        raise RuntimeError(
            f"SAFETY GUARD TRIGGERED: Refusing to run tests against suspected production database: {test_url}"
        )

    return test_url


@pytest.fixture(scope="session")
def test_engine():
    """Create test engine based on TEST_DATABASE_URL."""
    db_url = get_test_database_url()

    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL or other relational engine
        engine = create_engine(db_url, pool_pre_ping=True)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Provide an isolated, schema-clean database session per test."""
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
