"""Stock footage scene types for real YouTube video production.

These scene types use Pexels stock footage as backgrounds with FFmpeg text overlays,
instead of Manim-generated animations.
"""

from __future__ import annotations

from asset_orchestrator.scene_registry import BaseScene


class StockVideoScene(BaseScene):
    """Stock footage background with optional title overlay."""

    def construct(self) -> None:
        self.keywords = self.data.get("keywords", [])


class StockWithTextScene(BaseScene):
    """Stock footage with heading + body text overlay."""

    def construct(self) -> None:
        self.heading = self.data.get("heading", "")
        self.body = self.data.get("body", "")
        self.keywords = self.data.get("keywords", [])


class StockWithStatScene(BaseScene):
    """Stock footage with large stat value + label overlay."""

    def construct(self) -> None:
        self.stat_value = self.data.get("value", "0")
        self.stat_label = self.data.get("label", "")
        self.subtitle = self.data.get("subtitle", "")
        self.keywords = self.data.get("keywords", [])


class StockQuoteScene(BaseScene):
    """Stock footage with styled quote + attribution overlay."""

    def construct(self) -> None:
        self.quote_text = self.data.get("quote", "")
        self.attribution = self.data.get("attribution", "")
        self.keywords = self.data.get("keywords", [])
