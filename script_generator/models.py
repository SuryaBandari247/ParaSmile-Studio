"""
Data models for the Script Converter.

Defines the core dataclasses used throughout the script conversion pipeline:
SceneBlock for individual scenes and VideoScript for the complete script structure.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SceneBlock:
    """
    A single scene unit within a video script.

    Attributes:
        scene_number: Sequential scene identifier (1-based).
        narration_text: The spoken narration for this scene.
        visual_instruction: Directive for the Asset Orchestrator with keys:
            type, title, data, and optional style.
        emotion: Fish Audio emotion tag for TTS expressiveness.
            One of: neutral, happy, excited, confident, curious, calm,
            serious, surprised, empathetic, sarcastic, worried, frustrated.
    """

    scene_number: int
    narration_text: str
    visual_instruction: dict
    emotion: str = "neutral"


@dataclass
class VideoScript:
    """
    A complete structured video script containing ordered scenes.

    Attributes:
        title: The video title.
        scenes: Ordered list of SceneBlock instances (5-10 scenes).
        generated_at: UTC timestamp of when the script was generated.
        total_word_count: Sum of narration words across all scenes.
        metadata: Optional extra context for the script.
    """

    title: str
    scenes: list[SceneBlock]
    generated_at: datetime
    total_word_count: int
    metadata: dict = field(default_factory=dict)
