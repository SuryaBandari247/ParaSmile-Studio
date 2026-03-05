"""SceneExpander — auto-pads short high-impact scenes with breathing room.

Operates at the orchestrator layer, after audio duration is known but before
codegen. Extends target_duration for data-heavy scenes that would otherwise
feel rushed.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

HIGH_IMPACT_TYPES: set[str] = {
    "data_chart", "timeseries", "forensic_zoom", "volatility_shadow",
    "bull_bear_projection", "liquidity_shock", "compounding_explosion",
}

DEFAULT_PAD_S: float = 2.5
MIN_DURATION_THRESHOLD_S: float = 6.0


class SceneExpander:
    """Expands short high-impact scenes by adding padding to target_duration."""

    def expand_if_needed(
        self,
        narration_duration_s: float,
        visual_type: str,
        style_overrides: dict | None = None,
    ) -> float:
        """Return the final target_duration.

        If narration < threshold and type is high-impact, adds padding.
        Reads SCENE_EXPANSION_PAD_S from env, overridable via
        style_overrides['expansion_pad_s'].
        """
        overrides = style_overrides or {}
        pad = overrides.get(
            "expansion_pad_s",
            float(os.getenv("SCENE_EXPANSION_PAD_S", str(DEFAULT_PAD_S))),
        )

        if narration_duration_s < MIN_DURATION_THRESHOLD_S and visual_type in HIGH_IMPACT_TYPES:
            final = narration_duration_s + pad
            logger.info(
                "Scene expansion: %.1fs + %.1fs pad = %.1fs (type=%s)",
                narration_duration_s, pad, final, visual_type,
            )
            return final

        return narration_duration_s
