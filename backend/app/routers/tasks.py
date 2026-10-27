import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.cache import CacheService, get_cache
from app.database import get_db
from app.rate_limiter import rate_limit_task_creation
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskService,
    TaskValidationError,
)

logger = logging.getLogger("taskflow.tasks")

router = APIRouter()


def log_task_reminder(task_id: uuid.UUID, title: str, due_date: datetime):
    """Simulated reminder worker function that logs when a task reminder is triggered.

    WARNING: When executed via FastAPI BackgroundTasks, this runs in-process after the response
    is sent. If the server process crashes or restarts, any pending background tasks in memory are lost!
    """
    logger.info(f"[REMINDER] Task '{title}' (ID: {task_id}) is due at {due_date.isoformat()}")


@router.post(
    "",
    response_model=TaskResponse,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_task_creation)],
)
def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Create a new task. If a due date is specified, schedule an in-process reminder."""
    try:
        task = TaskService.create_task(
            db=db,
            user_id=payload.user_id,
            title=payload.title,
            description=payload.description,
            project_id=payload.project_id,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
        )
    except TaskValidationError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Invalidate project summary cache if task belongs to a project
    if task.project_id:
        cache.invalidate_project_summary(task.project_id)

    # Schedule reminder if due_date is provided
    if task.due_date is not None:
        background_tasks.add_task(log_task_reminder, task.id, task.title, task.due_date)

    return task


@router.get("", response_model=TaskListResponse, status_code=http_status.HTTP_200_OK)
def list_tasks(
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by owner user ID"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (todo, in_progress, done)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high)"),
    search: Optional[str] = Query(None, description="Search term in title or description"),
    limit: int = Query(20, ge=1, le=100, description="Items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """List tasks with pagination, search, and status/priority filters."""
    try:
        items, total = TaskService.list_tasks(
            db=db,
            user_id=user_id,
            project_id=project_id,
            status=status,
            priority=priority,
            search=search,
            limit=limit,
            offset=offset,
        )
    except TaskValidationError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=TaskResponse, status_code=http_status.HTTP_200_OK)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieve details of a single task by ID."""
    try:
        return TaskService.get_task(db, task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{task_id}", response_model=TaskResponse, status_code=http_status.HTTP_200_OK)
@router.patch("/{task_id}", response_model=TaskResponse, status_code=http_status.HTTP_200_OK)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Partially update an existing task with status transition validation."""
    update_data = payload.model_dump(exclude_unset=True)
    try:
        task = TaskService.update_task(db, task_id, update_data)
        if task.project_id:
            cache.invalidate_project_summary(task.project_id)
        return task
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InvalidStatusTransitionError, TaskValidationError) as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Delete a task by ID."""
    try:
        task = TaskService.get_task(db, task_id)
        project_id = task.project_id
        TaskService.delete_task(db, task_id)
        if project_id:
            cache.invalidate_project_summary(project_id)
        return None
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))
