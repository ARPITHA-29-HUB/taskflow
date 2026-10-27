"""
Task Service Layer Module
-------------------------
Implements core business logic for Task management, status transition lifecycle,
validation, and queries isolated from HTTP transport.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task
from app.models.user import User


class TaskNotFoundError(Exception):
    """Raised when a requested task does not exist."""

    def __init__(self, task_id: uuid.UUID | str):
        self.task_id = task_id
        super().__init__(f"Task with ID '{task_id}' was not found.")


class InvalidStatusTransitionError(Exception):
    """Raised when an illegal or unsupported status transition is attempted."""

    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition task status from '{current_status}' to '{new_status}'.")


class TaskValidationError(Exception):
    """Raised when task payload violates domain validation rules."""

    pass


# Domain Constants
VALID_STATUSES: Set[str] = {"todo", "in_progress", "done"}
VALID_PRIORITIES: Set[str] = {"low", "medium", "high"}

# Allowed transitions between valid statuses
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "todo": {"in_progress", "done"},
    "in_progress": {"todo", "done"},
    "done": {"in_progress", "todo"},
}


class TaskService:
    """Service encapsulating Task entity domain operations and queries."""

    @staticmethod
    def validate_status_transition(current_status: str, new_status: str) -> None:
        """Validate whether changing status from current_status to new_status is allowed.

        Rules:
        - new_status must be a recognized status.
        - transitioning to the exact same status is an allowed no-op.
        - transition must be declared in VALID_TRANSITIONS.
        """
        if new_status not in VALID_STATUSES:
            raise InvalidStatusTransitionError(current_status, new_status)

        if current_status == new_status:
            return

        allowed_targets = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed_targets:
            raise InvalidStatusTransitionError(current_status, new_status)

    @classmethod
    def get_task(cls, db: Session, task_id: uuid.UUID) -> Task:
        """Fetch a single task by ID or raise TaskNotFoundError."""
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            raise TaskNotFoundError(task_id)
        return task

    @classmethod
    def list_tasks(
        cls,
        db: Session,
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Task], int]:
        """Retrieve paginated and filtered tasks with total count."""
        query = db.query(Task)

        if user_id:
            query = query.filter(Task.user_id == user_id)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if status:
            if status not in VALID_STATUSES:
                raise TaskValidationError(f"Invalid status filter '{status}'.")
            query = query.filter(Task.status == status)
        if priority:
            if priority not in VALID_PRIORITIES:
                raise TaskValidationError(f"Invalid priority filter '{priority}'.")
            query = query.filter(Task.priority == priority)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(Task.title.ilike(term) | Task.description.ilike(term))

        total = query.count()
        items = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @classmethod
    def create_task(
        cls,
        db: Session,
        user_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        status: str = "todo",
        priority: str = "medium",
        due_date: Optional[datetime] = None,
    ) -> Task:
        """Create and persist a new task with domain validation."""
        clean_title = title.strip() if title else ""
        if not clean_title:
            raise TaskValidationError("Task title cannot be empty.")
        if len(clean_title) > 255:
            raise TaskValidationError("Task title cannot exceed 255 characters.")

        if status not in VALID_STATUSES:
            raise TaskValidationError(f"Invalid initial status '{status}'.")
        if priority not in VALID_PRIORITIES:
            raise TaskValidationError(f"Invalid priority '{priority}'.")

        # Verify foreign keys
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise TaskValidationError(f"User with ID '{user_id}' does not exist.")

        if project_id:
            project = db.query(Project).filter_by(id=project_id).first()
            if not project:
                raise TaskValidationError(f"Project with ID '{project_id}' does not exist.")

        task = Task(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=project_id,
            title=clean_title,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
        )
        db.add(task)
        try:
            db.commit()
            db.refresh(task)
        except IntegrityError as exc:
            db.rollback()
            raise TaskValidationError(f"Database integrity failure: {exc}")

        return task

    @classmethod
    def update_task_status(cls, db: Session, task_id: uuid.UUID, new_status: str) -> Task:
        """Update a task's status with transition lifecycle enforcement."""
        task = cls.get_task(db, task_id)
        cls.validate_status_transition(task.status, new_status)
        task.status = new_status
        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def update_task(cls, db: Session, task_id: uuid.UUID, update_fields: dict) -> Task:
        """Partially update task fields, enforcing validation and status transitions."""
        task = cls.get_task(db, task_id)

        if "status" in update_fields and update_fields["status"] is not None:
            new_status = update_fields["status"]
            cls.validate_status_transition(task.status, new_status)
            task.status = new_status

        if "priority" in update_fields and update_fields["priority"] is not None:
            new_priority = update_fields["priority"]
            if new_priority not in VALID_PRIORITIES:
                raise TaskValidationError(f"Invalid priority '{new_priority}'.")
            task.priority = new_priority

        if "title" in update_fields and update_fields["title"] is not None:
            clean_title = update_fields["title"].strip()
            if not clean_title:
                raise TaskValidationError("Task title cannot be empty.")
            task.title = clean_title

        if "description" in update_fields:
            task.description = update_fields["description"]

        if "due_date" in update_fields:
            task.due_date = update_fields["due_date"]

        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def delete_task(cls, db: Session, task_id: uuid.UUID) -> bool:
        """Delete a task by ID or raise TaskNotFoundError."""
        task = cls.get_task(db, task_id)
        db.delete(task)
        db.commit()
        return True
