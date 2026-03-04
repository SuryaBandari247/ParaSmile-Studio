"""
JSON serialization and deserialization for VideoScript.

Provides round-trip conversion between VideoScript dataclasses and JSON strings,
with ISO 8601 timestamp formatting and ParseError on invalid input.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import json
from datetime import datetime, timezone

from script_generator.exceptions import ParseError
from script_generator.models import SceneBlock, VideoScript


class ScriptSerializer:
    """Round-trip JSON serializer for VideoScript objects."""

    def serialize(self, script: VideoScript) -> str:
        """Convert a VideoScript to a JSON string with ISO 8601 timestamps.

        Args:
            script: The VideoScript dataclass to serialize.

        Returns:
            A JSON string representation of the VideoScript.
        """
        data = {
            "title": script.title,
            "scenes": [
                {
                    "scene_number": scene.scene_number,
                    "narration_text": scene.narration_text,
                    "emotion": scene.emotion,
                    "visual_instruction": scene.visual_instruction,
                }
                for scene in script.scenes
            ],
            "generated_at": script.generated_at.isoformat(),
            "total_word_count": script.total_word_count,
            "metadata": script.metadata,
        }
        return json.dumps(data)

    def deserialize(self, json_str: str) -> VideoScript:
        """Parse a JSON string into a VideoScript dataclass.

        Args:
            json_str: A JSON string to parse.

        Returns:
            A VideoScript instance.

        Raises:
            ParseError: If the JSON is malformed or required fields are missing/invalid.
        """
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ParseError(f"Malformed JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ParseError("JSON root must be an object")

        if "title" not in data:
            raise ParseError("Missing required field: title")

        if "scenes" not in data:
            raise ParseError("Missing required field: scenes")

        if not isinstance(data["title"], str):
            raise ParseError("Field 'title' must be a string")

        if not isinstance(data["scenes"], list):
            raise ParseError("Field 'scenes' must be a list")

        scenes: list[SceneBlock] = []
        for i, scene_data in enumerate(data["scenes"]):
            if not isinstance(scene_data, dict):
                raise ParseError(f"Scene {i} must be an object")
            for key in ("scene_number", "narration_text", "visual_instruction"):
                if key not in scene_data:
                    raise ParseError(f"Scene {i} missing required field: {key}")
            scenes.append(
                SceneBlock(
                    scene_number=scene_data["scene_number"],
                    narration_text=scene_data["narration_text"],
                    visual_instruction=scene_data["visual_instruction"],
                    emotion=scene_data.get("emotion", "neutral"),
                )
            )

        generated_at_raw = data.get("generated_at")
        if generated_at_raw is None:
            generated_at = datetime.now(timezone.utc)
        else:
            try:
                generated_at = datetime.fromisoformat(generated_at_raw)
            except (ValueError, TypeError) as exc:
                raise ParseError(f"Invalid generated_at timestamp: {exc}") from exc

        total_word_count = data.get("total_word_count", 0)
        metadata = data.get("metadata", {})

        return VideoScript(
            title=data["title"],
            scenes=scenes,
            generated_at=generated_at,
            total_word_count=total_word_count,
            metadata=metadata,
        )
