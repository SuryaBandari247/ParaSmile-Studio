"""StaticFreezeDetector — appends a hold for high-delta fast narration scenes.

Operates at the codegen layer. When a scene contains a data delta >= 10%
delivered in under 3 seconds of narration, appends a static freeze to give
the viewer time to visually retain the key data point.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

DEFAULT_FREEZE_S: float = 2.0
DELTA_THRESHOLD_PCT: float = 10.0
MAX_NARRATION_S: float = 3.0


class StaticFreezeDetector:
    """Detects high-delta data points and recommends a freeze duration."""

    def detect_freeze(
        self,
        instruction: dict,
        narration_duration_s: float,
        style_overrides: dict | None = None,
    ) -> float | None:
        """Return freeze duration in seconds if conditions are met, else None.

        Conditions: abs(data_delta) >= 10% AND narration_duration < 3s.
        """
        overrides = style_overrides or {}
        freeze_s = overrides.get(
            "freeze_duration_s",
            float(os.getenv("STATIC_FREEZE_S", str(DEFAULT_FREEZE_S))),
        )

        delta = self.extract_delta(instruction)
        if delta is None:
            return None

        if abs(delta) >= DELTA_THRESHOLD_PCT and narration_duration_s < MAX_NARRATION_S:
            logger.info(
                "Static freeze: delta=%.1f%%, narration=%.1fs → %.1fs freeze",
                delta, narration_duration_s, freeze_s,
            )
            return freeze_s

        return None

    def extract_delta(self, instruction: dict) -> float | None:
        """Inspect instruction data for percentage deltas."""
        data = instruction.get("data", {})

        # Check events for delta annotations
        for event in data.get("events", []):
            label = event.get("label", "")
            match = re.search(r'(-?\d+(?:\.\d+)?)\s*%', label)
            if match:
                return float(match.group(1))

        # Check annotations
        for ann in data.get("annotations", []):
            text = ann.get("text", ann.get("label", ""))
            match = re.search(r'(-?\d+(?:\.\d+)?)\s*%', text)
            if match:
                return float(match.group(1))

        # Check narration text
        narration = instruction.get("narration", "")
        match = re.search(r'(-?\d+(?:\.\d+)?)\s*(?:percent|%)', narration, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Check chart metadata
        delta_val = data.get("delta_pct") or data.get("change_pct")
        if delta_val is not None:
            try:
                return float(delta_val)
            except (ValueError, TypeError):
                pass

        return None
