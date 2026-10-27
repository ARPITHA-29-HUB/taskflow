import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str | None = Field(None, max_length=5000, description="Optional task description")
    user_id: uuid.UUID = Field(..., description="Owner user ID")
    project_id: uuid.UUID | None = Field(None, description="Optional associated project ID")
    status: str = Field("todo", pattern="^(todo|in_progress|done)$", description="Task status")
    priority: str = Field("medium", pattern="^(low|medium|high)$", description="Task priority")
    due_date: datetime | None = Field(None, description="Optional due date timestamp")


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated task title")
    description: Optional[str] = Field(None, max_length=5000, description="Updated description")
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$", description="Updated task status")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$", description="Updated task priority")
    due_date: Optional[datetime] = Field(None, description="Updated due date timestamp")


class TaskResponse(BaseModel):
    """Schema for returning task details to API clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated list response for tasks."""

    items: List[TaskResponse]
    total: int
    limit: int
    offset: int
