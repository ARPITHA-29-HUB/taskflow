import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.cache import get_cache, CacheService
from app.rate_limiter import rate_limit_task_creation
from app.models.task import Task
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse

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
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_task_creation)],
)
def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Create a new task. If a due date is specified, schedule an in-process reminder."""
    # 1. Verify user exists
    user = db.query(User).filter_by(id=payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with ID '{payload.user_id}' does not exist.",
        )

    # 2. Verify project exists if project_id is provided
    if payload.project_id:
        project = db.query(Project).filter_by(id=payload.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with ID '{payload.project_id}' does not exist.",
            )

    # 3. Create Task instance
    task = Task(
        id=uuid.uuid4(),
        user_id=payload.user_id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(task)
    try:
        db.commit()
        db.refresh(task)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error while creating task.",
        )

    # 4. Invalidate project summary cache if task belongs to a project
    if task.project_id:
        cache.invalidate_project_summary(task.project_id)

    # 5. Schedule reminder if due_date is provided (prevents duplicate or empty triggers)
    if task.due_date is not None:
        background_tasks.add_task(log_task_reminder, task.id, task.title, task.due_date)

    return task
