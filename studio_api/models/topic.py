"""Topic models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TopicStatus(str, Enum):
    PENDING = "PENDING"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    source: str = Field(default="manual")
    score: float = Field(default=0.0)
    keywords: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: TopicStatus | None = None


class TopicResponse(BaseModel):
    id: str
    project_id: str
    title: str
    source: str
    score: float
    keywords: list[str]
    status: TopicStatus
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
