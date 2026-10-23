import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

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
    return project
