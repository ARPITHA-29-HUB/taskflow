import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: str | None = Field(None, max_length=1000, description="Optional description")
    user_id: uuid.UUID = Field(..., description="Owner user ID")


class ProjectUpdate(BaseModel):
    """Schema for partially updating a project."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Updated project name")
    description: str | None = Field(None, max_length=1000, description="Updated description")


class ProjectResponse(BaseModel):
    """Schema for returning project data to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated response envelope for projects."""

    items: list[ProjectResponse]
    total: int
    limit: int
    offset: int


class ProjectSummaryResponse(BaseModel):
    """Aggregated task counts by status for a project."""

    project_id: uuid.UUID
    total_tasks: int
    todo: int
    in_progress: int
    done: int
