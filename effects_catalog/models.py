"""Core data models for the Effects Catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EffectCategory(str, Enum):
    """Grouping label for effects used in browsing and filtering."""

    CHARTS = "charts"
    TEXT = "text"
    SOCIAL = "social"
    DATA = "data"
    EDITORIAL = "editorial"
    NARRATIVE = "narrative"
    MOTION = "motion"


# Default quality profiles for M4 48GB hardware
DEFAULT_QUALITY_PROFILES: dict[str, dict] = {
    "draft": {
        "resolution": "720p",
        "fps": 15,
        "manim_quality": "-ql",
        "encoder": "libx264",
    },
    "production": {
        "resolution": "1080p",
        "fps": 30,
        "manim_quality": "-qh",
        "encoder": "h264_videotoolbox",
    },
}


@dataclass
class EffectSkeleton:
    """A parameterized Manim scene template — the atomic unit of the effects library.

    Each skeleton defines the animation structure, accepted parameters, default
    styles, preview configuration, and rendering metadata for a single reusable
    effect.
    """

    identifier: str
    display_name: str
    category: EffectCategory
    description: str
    parameter_schema: dict = field(default_factory=dict)
    preview_config: dict = field(default_factory=dict)
    reference_video_path: str = ""
    template_module: str = ""
    sync_points: list[str] = field(default_factory=list)
    quality_profiles: dict[str, dict] = field(
        default_factory=lambda: dict(DEFAULT_QUALITY_PROFILES)
    )
    initial_wait: float = 0.0
