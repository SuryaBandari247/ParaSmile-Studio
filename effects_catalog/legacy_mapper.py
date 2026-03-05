"""LegacyMapper — backward-compatible alias resolution for deprecated scene type strings."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LegacyMapper:
    """Routes deprecated scene type strings to the correct EffectSkeleton identifier.

    Supports two mapping styles in legacy_mappings.json:
      - Simple alias:   {"line_chart": {"target": "timeseries"}}
      - Sub-type dispatch: {"data_chart": {"sub_type_field": "chart_type", "mappings": {...}, "default": "timeseries"}}
    """

    def __init__(self, mappings_path: str | Path = "effects_catalog/legacy_mappings.json"):
        self._mappings: dict = {}
        self._load(Path(mappings_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Legacy mappings not found at %s", path)
            return
        try:
            self._mappings = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load legacy mappings: %s", exc)

    def resolve(self, type_string: str, instruction: dict | None = None) -> str | None:
        """Return the mapped skeleton identifier for a legacy type string.

        Returns None if type_string is not a legacy alias.
        For sub-type mappings, inspects instruction[sub_type_field].
        Logs deprecation warning on successful resolution.
        """
        entry = self._mappings.get(type_string)
        if entry is None:
            return None

        # Simple alias: {"target": "timeseries"}
        if "target" in entry:
            target = entry["target"]
            logger.warning("Deprecated type '%s' → '%s'", type_string, target)
            return target

        # Sub-type dispatch: {"sub_type_field": ..., "mappings": {...}, "default": ...}
        sub_field = entry.get("sub_type_field", "chart_type")
        mappings = entry.get("mappings", {})
        default = entry.get("default")

        sub_value = None
        if instruction:
            sub_value = instruction.get("data", {}).get(sub_field) or instruction.get(sub_field)

        target = mappings.get(sub_value, default) if sub_value else default
        if target:
            logger.warning(
                "Deprecated type '%s' (sub_type=%s) → '%s'",
                type_string, sub_value, target,
            )
        return target
    def list_aliases(self) -> dict[str, str]:
        """Return flat alias → target mapping for the Effect Browser.

        Sub-type dispatch entries use their default target.
        """
        result: dict[str, str] = {}
        for alias, entry in self._mappings.items():
            if "target" in entry:
                result[alias] = entry["target"]
            elif "default" in entry:
                result[alias] = entry["default"]
        return result
