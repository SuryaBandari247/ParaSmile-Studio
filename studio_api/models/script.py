"""Script version models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScriptVersionCreate(BaseModel):
    topic_id: str
    title: str = Field(..., min_length=1, max_length=300)
    script_json: dict[str, Any]
    source_version_id: int | None = None  # for duplicating


class ScriptVersionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    script_json: dict[str, Any] | None = None


class ScriptVersionResponse(BaseModel):
    id: int
    project_id: str
    topic_id: str
    version: int
    title: str
    script_json: dict[str, Any]
    is_finalized: bool
    created_at: str


class DiffResult(BaseModel):
    version_a: int
    version_b: int
    changes: list[dict[str, Any]]
