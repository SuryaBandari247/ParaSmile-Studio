"""SSMLDataPauseInjector — inserts <break> tags after high-impact data phrases.

Operates at the audio layer, preprocessing narration text before TTS synthesis.
Detects percentage values >= 10% and currency values >= $1B, inserting pauses
to give the visual engine time to animate the corresponding data point.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

DEFAULT_PAUSE_MS: int = 1000
MAX_SCENE_DURATION_S: float = 8.0

PCT_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:percent|%)', re.IGNORECASE,
)
CURRENCY_PATTERN = re.compile(
    r'\$\s*(\d+(?:\.\d+)?)\s*(billion|trillion|B|T)', re.IGNORECASE,
)


class SSMLDataPauseInjector:
    """Injects <break> tags after high-impact data phrases in narration text."""

    def inject_pauses(
        self,
        narration_text: str,
        scene_duration_s: float | None = None,
        data_pause_ms: int | None = None,
    ) -> str:
        """Return narration text with <break> tags after high-impact phrases.

        Skips injection if scene_duration_s >= MAX_SCENE_DURATION_S.
        Reads DATA_PAUSE_MS from env if data_pause_ms not provided.
        """
        if scene_duration_s is not None and scene_duration_s >= MAX_SCENE_DURATION_S:
            return narration_text

        pause_ms = data_pause_ms or int(os.getenv("DATA_PAUSE_MS", str(DEFAULT_PAUSE_MS)))
        break_tag = f' <break time="{pause_ms}ms"/>'

        result = narration_text

        # Process percentage patterns (>= 10%)
        def _replace_pct(match: re.Match) -> str:
            value = float(match.group(1))
            if abs(value) >= 10:
                logger.info("SSML pause: detected '%s' (%.1f%%)", match.group(0), value)
                return match.group(0) + break_tag
            return match.group(0)

        result = PCT_PATTERN.sub(_replace_pct, result)

        # Process currency patterns (>= $1B)
        def _replace_currency(match: re.Match) -> str:
            value = float(match.group(1))
            unit = match.group(2).lower()
            if unit in ("billion", "b") and value >= 1:
                logger.info("SSML pause: detected '%s'", match.group(0))
                return match.group(0) + break_tag
            if unit in ("trillion", "t"):
                logger.info("SSML pause: detected '%s'", match.group(0))
                return match.group(0) + break_tag
            return match.group(0)

        result = CURRENCY_PATTERN.sub(_replace_currency, result)

        return result
