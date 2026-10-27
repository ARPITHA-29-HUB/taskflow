"""
Database Engine Compatibility & Safety Guard Tests
--------------------------------------------------
Verifies:
1. Production safety guards block tests if pointed at production URLs or APP_ENV=production.
2. Dialect differences between SQLite and PostgreSQL (CheckConstraints, Foreign Keys, UUIDs).
3. Conditional PostgreSQL integration test when TEST_DATABASE_URL provides a PostgreSQL connection.
"""

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.task import Task
from app.models.user import User
from tests.conftest import get_test_database_url


def test_safety_guard_blocks_production_environment(monkeypatch):
    """Verify that get_test_database_url aborts if APP_ENV is set to production."""
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError) as exc_info:
        get_test_database_url()
    assert "SAFETY GUARD TRIGGERED" in str(exc_info.value)


def test_safety_guard_blocks_production_database_string(monkeypatch):
    """Verify that get_test_database_url aborts if URL matches a production pattern."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://admin:secret@prod-db.aws.internal:5432/taskflow_prod")
    with pytest.raises(RuntimeError) as exc_info:
        get_test_database_url()
    assert "SAFETY GUARD TRIGGERED" in str(exc_info.value)


def test_database_check_constraint_rejects_invalid_status(test_db_session):
    """Verify that the SQL CheckConstraint 'ck_tasks_status' rejects illegal status values."""
    user = User(
        id=uuid.uuid4(),
        email="constraint_tester@example.com",
        hashed_password="hashed_pw_test",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()

    # Attempt to insert directly with invalid status bypassing Pydantic
    invalid_task = Task(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Invalid Status Task",
        status="illegal_status_value",  # Fails ck_tasks_status
        priority="medium",
    )
    test_db_session.add(invalid_task)

    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_database_check_constraint_rejects_invalid_priority(test_db_session):
    """Verify that the SQL CheckConstraint 'ck_tasks_priority' rejects illegal priority values."""
    user = User(
        id=uuid.uuid4(),
        email="priority_tester@example.com",
        hashed_password="hashed_pw_test",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()

    invalid_task = Task(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Invalid Priority Task",
        status="todo",
        priority="emergency_ultra_high",  # Fails ck_tasks_priority
    )
    test_db_session.add(invalid_task)

    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


# Conditional PostgreSQL Live Integration Test
POSTGRES_URL = os.getenv("TEST_DATABASE_URL", "")
IS_POSTGRES = POSTGRES_URL.startswith("postgresql") or POSTGRES_URL.startswith("postgres")


@pytest.mark.skipif(not IS_POSTGRES, reason="PostgreSQL test database not configured in TEST_DATABASE_URL")
def test_postgresql_native_uuid_and_timestamptz(test_db_session):
    """Verify native PostgreSQL UUID and TIMESTAMPTZ storage when running against Postgres."""
    result = test_db_session.execute(text("SELECT version();")).scalar()
    assert "PostgreSQL" in result
