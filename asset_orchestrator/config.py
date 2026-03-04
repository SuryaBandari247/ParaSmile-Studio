"""Data models and configuration for the Asset Orchestrator module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VisualInstruction:
    """A structured directive from a video script."""

    type: str
    title: str
    data: dict
    style: dict | None = None


@dataclass
class RenderConfig:
    """Manim rendering parameters."""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    output_dir: str = "output/renders"
    output_format: str = "mp4"


@dataclass
class CompositionConfig:
    """FFmpeg composition parameters."""

    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5M"
    audio_bitrate: str = "192k"
    output_dir: str = "output/composed"


@dataclass
class BatchResult:
    """Summary of a batch processing run."""

    total: int
    succeeded: int
    failed: int
    results: list[dict] = field(default_factory=list)
