"""Project models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    RENDERED = "RENDERED"
    PUBLISHED = "PUBLISHED"


class PipelineStage(str, Enum):
    RESEARCH = "RESEARCH"
    TOPIC = "TOPIC"
    SCRIPT = "SCRIPT"
    AUDIO = "AUDIO"
    VISUAL = "VISUAL"
    RENDER = "RENDER"


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None
    current_stage: PipelineStage | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    status: ProjectStatus
    current_stage: PipelineStage
    created_at: str
    updated_at: str
