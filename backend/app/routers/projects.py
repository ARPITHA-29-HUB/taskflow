import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.cache import get_cache, CacheService
from app.rate_limiter import rate_limit_task_creation
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectSummaryResponse,
)
from app.schemas.task import TaskCreate, TaskResponse
from app.routers.tasks import create_task

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project associated with a user."""
    # Verify that the user exists to prevent orphaned records or raw SQL foreign key errors
    user = db.query(User).filter_by(id=payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with ID '{payload.user_id}' does not exist.",
        )

    project = Project(
        id=uuid.uuid4(),
        user_id=payload.user_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)
    try:
        db.commit()
        db.refresh(project)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error while creating project.",
        )

    return project


@router.get("", response_model=ProjectListResponse, status_code=status.HTTP_200_OK)
def list_projects(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ID filter"),
    db: Session = Depends(get_db),
):
    """Retrieve a paginated list of projects, optionally filtered by user_id."""
    query = db.query(Project)
    if user_id:
        query = query.filter_by(user_id=user_id)

    total = query.count()
    items = query.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()

    return ProjectListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{project_id}", response_model=ProjectResponse, status_code=status.HTTP_200_OK)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Partially update an existing project's name or description."""
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' was not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return project

    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    # Invalidate cached summary upon project mutation
    cache.invalidate_project_summary(project_id)

    return project


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse, status_code=status.HTTP_200_OK)
def get_project_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Retrieve aggregated task counts for a project using Cache-Aside (60s TTL)."""
    cache_key = f"project:{project_id}:summary"

    # 1. Check cache first (Cache-Aside pattern)
    cached_summary = cache.get(cache_key)
    if cached_summary is not None:
        return cached_summary

    # 2. Verify project exists in database
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' was not found.",
        )

    # 3. Query Database for task counts by status
    status_counts = (
        db.query(Task.status, func.count(Task.id))
        .filter(Task.project_id == project_id)
        .group_by(Task.status)
        .all()
    )

    summary_map = {status: count for status, count in status_counts}
    todo_count = summary_map.get("todo", 0)
    in_progress_count = summary_map.get("in_progress", 0)
    done_count = summary_map.get("done", 0)
    total = todo_count + in_progress_count + done_count

    result = {
        "project_id": str(project_id),
        "total_tasks": total,
        "todo": todo_count,
        "in_progress": in_progress_count,
        "done": done_count,
    }

    # 4. Write result to cache with 60s TTL
    cache.set(cache_key, result, ttl=60)

    return result


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_task_creation)],
)
def create_task_for_project(
    project_id: uuid.UUID,
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Create a new task specifically within a project (enforces 30 req/min rate limit)."""
    payload.project_id = project_id
    return create_task(payload=payload, background_tasks=background_tasks, db=db, cache=cache)

