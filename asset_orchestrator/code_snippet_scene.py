"""Code Snippet Scene — renders syntax-highlighted code blocks.

Uses the same dark-background colour scheme as the chart templates
for visual consistency across all video assets.
"""

from __future__ import annotations

from asset_orchestrator.scene_registry import BaseScene

# Reuse colour constants from chart_templates for consistency
BACKGROUND_COLOR = "#333333"
TEXT_COLOR = "#FFFFFF"
MONOSPACE_FONT = "Courier New"
DEFAULT_LANGUAGE = "python"


class CodeSnippetScene(BaseScene):
    """Scene for syntax-highlighted code block animations.

    Attributes set after ``construct()``:
        processed_title: The scene title.
        code_text: The code string extracted from *data*.
        language: The programming language for syntax highlighting.
        background_color: Dark gray background (#333333).
        text_color: White text (#FFFFFF).
        font_family: Monospace font used for code rendering.
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        super().__init__(title=title, data=data, style=style)
        # Attributes populated by construct()
        self.processed_title: str | None = None
        self.code_text: str | None = None
        self.language: str | None = None
        self.background_color: str | None = None
        self.text_color: str | None = None
        self.font_family: str | None = None

    def construct(self) -> None:
        """Prepare the code-snippet animation data structures.

        Since we subclass ``BaseScene`` (not real Manim), this method stores
        what *would* be rendered as instance attributes so the logic can be
        verified in tests without a Manim installation.
        """
        self.processed_title = self.title
        self.code_text = self.data.get("code", "")
        self.language = self.data.get("language", DEFAULT_LANGUAGE)
        self.background_color = BACKGROUND_COLOR
        self.text_color = TEXT_COLOR
        self.font_family = MONOSPACE_FONT
