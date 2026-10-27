"""
Unit Tests for TaskService Domain Logic & Lifecycle Transitions
--------------------------------------------------------------
Covers:
- Valid status transitions (todo -> in_progress -> done, etc.)
- Invalid status transitions and unhandled status values
- Title, priority, and foreign key validations
- Missing task lookups (TaskNotFoundError)
- Service CRUD operations
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models.project import Project
from app.models.user import User
from app.services.task_service import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskService,
    TaskValidationError,
)


@pytest.fixture
def sample_user(test_db_session):
    user = User(
        id=uuid.uuid4(),
        email="services_user@example.com",
        hashed_password="hashed_pass_123",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def sample_project(test_db_session, sample_user):
    project = Project(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Service Test Project",
        description="Testing TaskService logic",
    )
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)
    return project


# 1. Status Transitions (Parametrized)


@pytest.mark.parametrize(
    "current_status,new_status",
    [
        ("todo", "in_progress"),
        ("in_progress", "done"),
        ("done", "in_progress"),
        ("todo", "done"),
        ("in_progress", "todo"),
        ("done", "todo"),
        ("todo", "todo"),  # Idempotent no-op
        ("in_progress", "in_progress"),
        ("done", "done"),
    ],
)
def test_valid_status_transitions(current_status, new_status):
    """Verify that all legitimate status transitions pass validation."""
    # Should not raise exception
    TaskService.validate_status_transition(current_status, new_status)


@pytest.mark.parametrize(
    "current_status,new_status",
    [
        ("todo", "archived"),
        ("in_progress", "cancelled"),
        ("done", "deleted"),
        ("todo", "unknown"),
        ("in_progress", ""),
    ],
)
def test_invalid_status_transitions_raise_error(current_status, new_status):
    """Verify that transitions to unsupported statuses raise InvalidStatusTransitionError."""
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        TaskService.validate_status_transition(current_status, new_status)
    assert current_status in str(exc_info.value)
    assert new_status in str(exc_info.value)


# 2. Validation & Edge Cases


def test_create_task_empty_title_raises_validation_error(test_db_session, sample_user):
    """Verify that creating a task with empty/whitespace title raises TaskValidationError."""
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(test_db_session, user_id=sample_user.id, title="   ")
    assert "cannot be empty" in str(exc.value)


def test_create_task_title_too_long_raises_validation_error(test_db_session, sample_user):
    """Verify that title exceeding 255 chars raises TaskValidationError."""
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(test_db_session, user_id=sample_user.id, title="A" * 256)
    assert "cannot exceed 255" in str(exc.value)


def test_create_task_invalid_priority_raises_validation_error(test_db_session, sample_user):
    """Verify that unsupported priority raises TaskValidationError."""
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(test_db_session, user_id=sample_user.id, title="Task", priority="urgent")
    assert "Invalid priority" in str(exc.value)


def test_create_task_nonexistent_user_raises_validation_error(test_db_session):
    """Verify that creating a task with nonexistent user_id raises TaskValidationError."""
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(test_db_session, user_id=uuid.uuid4(), title="Orphan Task")
    assert "does not exist" in str(exc.value)


def test_create_task_nonexistent_project_raises_validation_error(test_db_session, sample_user):
    """Verify that creating a task with nonexistent project_id raises TaskValidationError."""
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(
            test_db_session,
            user_id=sample_user.id,
            title="Invalid Project Task",
            project_id=uuid.uuid4(),
        )
    assert "does not exist" in str(exc.value)


# 3. Missing Task Handling


def test_get_nonexistent_task_raises_not_found(test_db_session):
    """Verify that querying a missing task raises TaskNotFoundError."""
    missing_id = uuid.uuid4()
    with pytest.raises(TaskNotFoundError) as exc:
        TaskService.get_task(test_db_session, missing_id)
    assert str(missing_id) in str(exc.value)


def test_update_nonexistent_task_raises_not_found(test_db_session):
    """Verify that updating a missing task raises TaskNotFoundError."""
    missing_id = uuid.uuid4()
    with pytest.raises(TaskNotFoundError):
        TaskService.update_task(test_db_session, missing_id, {"title": "Updated"})


def test_delete_nonexistent_task_raises_not_found(test_db_session):
    """Verify that deleting a missing task raises TaskNotFoundError."""
    missing_id = uuid.uuid4()
    with pytest.raises(TaskNotFoundError):
        TaskService.delete_task(test_db_session, missing_id)


# 4. End-to-End Service CRUD & Lifecycle


def test_task_lifecycle_crud(test_db_session, sample_user, sample_project):
    """Verify full task lifecycle: create -> read -> update status -> search -> delete."""
    # 1. Create
    task = TaskService.create_task(
        db=test_db_session,
        user_id=sample_user.id,
        project_id=sample_project.id,
        title="Lifecycle Task",
        description="Verify service lifecycle",
        status="todo",
        priority="high",
        due_date=datetime.now(timezone.utc),
    )
    assert task.id is not None
    assert task.status == "todo"

    # 2. Read
    fetched = TaskService.get_task(test_db_session, task.id)
    assert fetched.id == task.id

    # 3. Valid transition: todo -> in_progress
    updated = TaskService.update_task_status(test_db_session, task.id, "in_progress")
    assert updated.status == "in_progress"

    # 4. Partial update with transition: in_progress -> done
    updated_done = TaskService.update_task(
        test_db_session,
        task.id,
        {"title": "Completed Lifecycle Task", "status": "done"},
    )
    assert updated_done.title == "Completed Lifecycle Task"
    assert updated_done.status == "done"

    # 5. List with search & filter
    items, total = TaskService.list_tasks(
        db=test_db_session,
        project_id=sample_project.id,
        status="done",
        search="Completed",
    )
    assert total == 1
    assert items[0].id == task.id

    # 6. Delete
    deleted = TaskService.delete_task(test_db_session, task.id)
    assert deleted is True

    # 7. Confirm deleted
    with pytest.raises(TaskNotFoundError):
        TaskService.get_task(test_db_session, task.id)


def test_list_tasks_invalid_status_filter_raises_error(test_db_session):
    with pytest.raises(TaskValidationError) as exc:
        TaskService.list_tasks(test_db_session, status="nonexistent_status")
    assert "Invalid status filter" in str(exc.value)


def test_list_tasks_invalid_priority_filter_raises_error(test_db_session):
    with pytest.raises(TaskValidationError) as exc:
        TaskService.list_tasks(test_db_session, priority="nonexistent_priority")
    assert "Invalid priority filter" in str(exc.value)


def test_create_task_invalid_status_raises_validation_error(test_db_session, sample_user):
    with pytest.raises(TaskValidationError) as exc:
        TaskService.create_task(test_db_session, user_id=sample_user.id, title="Task", status="invalid_status")
    assert "Invalid initial status" in str(exc.value)


def test_update_task_invalid_priority_raises_validation_error(test_db_session, sample_user):
    task = TaskService.create_task(test_db_session, user_id=sample_user.id, title="Task Priority Test")
    with pytest.raises(TaskValidationError) as exc:
        TaskService.update_task(test_db_session, task.id, {"priority": "invalid_prio"})
    assert "Invalid priority" in str(exc.value)


def test_update_task_empty_title_raises_validation_error(test_db_session, sample_user):
    task = TaskService.create_task(test_db_session, user_id=sample_user.id, title="Task Title Test")
    with pytest.raises(TaskValidationError) as exc:
        TaskService.update_task(test_db_session, task.id, {"title": "   "})
    assert "Task title cannot be empty" in str(exc.value)


def test_update_task_fields_optional(test_db_session, sample_user):
    task = TaskService.create_task(test_db_session, user_id=sample_user.id, title="Task Fields Test")
    updated = TaskService.update_task(
        test_db_session,
        task.id,
        {"description": "New description", "due_date": None},
    )
    assert updated.description == "New description"
    assert updated.due_date is None
