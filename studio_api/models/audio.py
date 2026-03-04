"""Audio segment models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VoiceParams(BaseModel):
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    temperature: float = Field(default=0.6, ge=0.1, le=1.0)
    top_p: float = Field(default=0.7, ge=0.1, le=1.0)
    repetition_penalty: float = Field(default=1.4, ge=0.9, le=2.0)
    emotion: str = Field(default="neutral")
    # Legacy fields kept for backward compat with existing DB rows
    pitch: float = Field(default=0.0, ge=-1.0, le=1.0)
    emphasis: str = Field(default="none")


class AudioSegmentCreate(BaseModel):
    script_version_id: int
    scene_number: int
    start_time: str  # HH:MM:SS,mmm
    end_time: str
    narration_text: str
    voice_params: VoiceParams = Field(default_factory=VoiceParams)


class AudioSegmentUpdate(BaseModel):
    narration_text: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    voice_params: VoiceParams | None = None


class AudioSegmentResponse(BaseModel):
    id: int
    project_id: str
    script_version_id: int
    scene_number: int
    start_time: str
    end_time: str
    narration_text: str
    voice_params: VoiceParams | None = None
    audio_file_path: str | None = None
    status: str
    version: int
    created_at: str


class AudioTimelineResponse(BaseModel):
    segments: list[AudioSegmentResponse]
    total_duration: str  # HH:MM:SS,mmm
    segment_count: int
