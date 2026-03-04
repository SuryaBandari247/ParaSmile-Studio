"""Scene models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SceneUpdate(BaseModel):
    visual_type: str | None = None
    visual_data: dict[str, Any] | None = None
    stock_video_path: str | None = None
    transition: str | None = None
    effects: list[str] | None = None
    show_title: bool | None = None
    target_duration: float | None = None
    clip_count: int | None = None


class SceneCreate(BaseModel):
    visual_type: str = "stock_video"
    visual_data: dict[str, Any] = Field(default_factory=dict)
    target_duration: float | None = None
    clip_count: int = 0


class SceneResponse(BaseModel):
    id: int
    project_id: str
    scene_number: int
    visual_type: str
    visual_data: dict[str, Any]
    stock_video_path: str | None = None
    rendered_path: str | None = None
    thumbnail_path: str | None = None
    transition: str = "fade"
    effects: list[str] = []
    show_title: bool = False
    target_duration: float | None = None
    clip_count: int = 0
    duration: float | None = None
    status: str
    created_at: str
    updated_at: str


class FootageResult(BaseModel):
    video_id: int
    url: str
    preview_url: str
    duration: int
    width: int
    height: int


class WikimediaImageResult(BaseModel):
    title: str
    url: str
    thumb_url: str
    width: int
    height: int
    license: str
    attribution: str


class PixabayVideoResult(BaseModel):
    video_id: int
    url: str
    preview_url: str
    duration: int
    width: int
    height: int
    tags: str = ""


class UnsplashPhotoResult(BaseModel):
    photo_id: str
    url: str
    thumb_url: str
    page_url: str
    width: int
    height: int
    description: str = ""
    photographer: str = ""


class MusicSettings(BaseModel):
    volume: int = Field(default=30, ge=0, le=100)
    fade_in_ms: int = Field(default=2000, ge=0)
    fade_out_ms: int = Field(default=3000, ge=0)
