"""Job models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(str, Enum):
    RESEARCH_YOUTUBE = "research_youtube"
    RESEARCH_REDDIT = "research_reddit"
    RESEARCH_TRENDS = "research_trends"
    RESEARCH_FINANCE = "research_finance"
    RESEARCH_WIKIPEDIA = "research_wikipedia"
    CROSS_REFERENCE = "cross_reference"
    SYNTHESIZE_AUDIO = "synthesize_audio"
    RENDER_SCENE = "render_scene"
    RENDER_FINAL = "render_final"
    GENERATE_PITCH = "generate_pitch"


class JobResponse(BaseModel):
    id: str
    project_id: str
    job_type: str
    status: JobStatus
    input_json: Any | None = None
    output_json: Any | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class WebSocketMessage(BaseModel):
    event: str  # job_started, job_progress, job_completed, job_failed
    job_id: str
    job_type: str
    data: dict = {}
