"""Scene Mapper — parses Visual_Instructions and resolves them to Scene instances."""

from __future__ import annotations

import json
import logging

from asset_orchestrator.exceptions import ParseError, UnknownSceneTypeError, ValidationError
from asset_orchestrator.scene_registry import BaseScene, SceneRegistry

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("type", "title", "data")


class SceneMapper:
    """Parses Visual_Instructions and resolves them to Manim Scene instances."""

    def __init__(self, registry: SceneRegistry) -> None:
        """
        Args:
            registry: Scene registry for type lookups.
        """
        self._registry = registry

    def map(self, instruction: dict) -> BaseScene:
        """Validate a Visual_Instruction and return a configured Scene.

        Args:
            instruction: Dict with keys: type, title, data, style (optional).

        Returns:
            An instantiated Scene configured with the instruction's
            title, data, and style.

        Raises:
            ValidationError: If required fields are missing.
            UnknownSceneTypeError: If type is not in the registry.
        """
        missing = [f for f in _REQUIRED_FIELDS if f not in instruction]
        if missing:
            raise ValidationError(missing)

        logger.info(
            "Instruction received: type=%s, title=%s",
            instruction["type"],
            instruction["title"],
        )

        scene_cls = self._registry.get(instruction["type"])
        return scene_cls(
            title=instruction["title"],
            data=instruction["data"],
            style=instruction.get("style"),
        )

    def serialize(self, instruction: dict) -> str:
        """Serialize a Visual_Instruction dict to a JSON string.

        Args:
            instruction: Visual_Instruction dict.

        Returns:
            JSON string.
        """
        return json.dumps(instruction)

    def deserialize(self, json_str: str) -> dict:
        """Deserialize a JSON string to a Visual_Instruction dict.

        Args:
            json_str: JSON string.

        Returns:
            Visual_Instruction dict.

        Raises:
            ParseError: If JSON is malformed, with the character position
                of the syntax error.
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ParseError(position=exc.pos, message=exc.msg) from exc
