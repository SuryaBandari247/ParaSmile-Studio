"""Data models for the Voice Synthesizer module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SceneAudio:
    """A single scene's synthesized audio result."""

    scene_number: int
    file_path: str | None  # Absolute path, None if synthesis failed
    duration_seconds: float  # 0.0 if failed
    char_count: int  # Character count of narration text
    error: str | None = None  # Error message if synthesis failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_number": self.scene_number,
            "file_path": self.file_path,
            "duration_seconds": self.duration_seconds,
            "char_count": self.char_count,
            "error": self.error,
        }


@dataclass
class AudioManifest:
    """Manifest mapping scenes to audio files with summary metadata."""

    entries: list[SceneAudio]
    total_duration_seconds: float
    total_scenes_synthesized: int
    total_scenes_failed: int
    total_characters_processed: int
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_audio_path(self, scene_number: int) -> str | None:
        """Return file path for a scene number, or None if not found/failed."""
        for entry in self.entries:
            if entry.scene_number == scene_number and entry.file_path is not None:
                return entry.file_path
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_duration_seconds": self.total_duration_seconds,
            "total_scenes_synthesized": self.total_scenes_synthesized,
            "total_scenes_failed": self.total_scenes_failed,
            "total_characters_processed": self.total_characters_processed,
            "generated_at": self.generated_at.isoformat(),
        }
