"""Text Overlay Scene — renders text overlays with configurable style.

Uses the same dark-background colour scheme as the chart templates
for visual consistency across all video assets.
"""

from __future__ import annotations

from asset_orchestrator.scene_registry import BaseScene

# Reuse colour constants from chart_templates for consistency
BACKGROUND_COLOR = "#333333"
TEXT_COLOR = "#FFFFFF"
DEFAULT_FONT_SIZE = 48
DEFAULT_POSITION = "center"
DEFAULT_ANIMATION = "fade_in"


class TextOverlayScene(BaseScene):
    """Scene for text overlay animations.

    Attributes set after ``construct()``:
        processed_title: The scene title.
        text_content: The text string extracted from *data*.
        font_size: Font size from *style* or default (48).
        position: Text position from *style* or default ("center").
        animation: Animation type from *style* or default ("fade_in").
        background_color: Dark gray background (#333333).
        text_color: White text (#FFFFFF).
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        super().__init__(title=title, data=data, style=style)
        # Attributes populated by construct()
        self.processed_title: str | None = None
        self.text_content: str | None = None
        self.font_size: int | None = None
        self.position: str | None = None
        self.animation: str | None = None
        self.background_color: str | None = None
        self.text_color: str | None = None

    def construct(self) -> None:
        """Prepare the text-overlay animation data structures.

        Since we subclass ``BaseScene`` (not real Manim), this method stores
        what *would* be rendered as instance attributes so the logic can be
        verified in tests without a Manim installation.
        """
        style = self.style or {}

        self.processed_title = self.title
        self.text_content = self.data.get("text", "")
        self.font_size = style.get("font_size", DEFAULT_FONT_SIZE)
        self.position = style.get("position", DEFAULT_POSITION)
        self.animation = style.get("animation", DEFAULT_ANIMATION)
        self.background_color = BACKGROUND_COLOR
        self.text_color = TEXT_COLOR
