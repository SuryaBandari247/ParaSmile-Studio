"""YouTube-style scene types for automated video production.

Scene types designed for real YouTube content — not academic charts.
All subclass BaseScene for registry compatibility.
"""

from __future__ import annotations

from asset_orchestrator.scene_registry import BaseScene

BACKGROUND_COLOR = "#1a1a2e"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#e94560"
SECONDARY_COLOR = "#0f3460"
MUTED_COLOR = "#888888"


class RedditPostScene(BaseScene):
    """Mockup of a Reddit post with subreddit, title, votes, comments."""

    def construct(self) -> None:
        self.subreddit = self.data.get("subreddit", "r/unknown")
        self.post_title = self.data.get("post_title", "")
        self.upvotes = self.data.get("upvotes", 0)
        self.comments = self.data.get("comments", 0)
        self.username = self.data.get("username", "u/anonymous")


class StatCalloutScene(BaseScene):
    """Big dramatic number with label — e.g. '$10,000 OWED'."""

    def construct(self) -> None:
        self.stat_value = self.data.get("value", "0")
        self.stat_label = self.data.get("label", "")
        self.subtitle = self.data.get("subtitle", "")


class QuoteBlockScene(BaseScene):
    """Styled quote with optional attribution."""

    def construct(self) -> None:
        self.quote_text = self.data.get("quote", "")
        self.attribution = self.data.get("attribution", "")
        self.style_variant = self.data.get("variant", "default")


class SectionTitleScene(BaseScene):
    """Full-screen section header with subtitle."""

    def construct(self) -> None:
        self.heading = self.data.get("heading", "")
        self.subtitle = self.data.get("subtitle", "")
        self.number = self.data.get("number", "")


class BulletRevealScene(BaseScene):
    """Animated bullet points that build one by one."""

    def construct(self) -> None:
        self.bullets = self.data.get("bullets", [])
        self.heading = self.data.get("heading", "")


class ComparisonScene(BaseScene):
    """Side-by-side comparison layout."""

    def construct(self) -> None:
        self.left_title = self.data.get("left_title", "")
        self.left_items = self.data.get("left_items", [])
        self.right_title = self.data.get("right_title", "")
        self.right_items = self.data.get("right_items", [])


class FullscreenStatementScene(BaseScene):
    """Single powerful sentence, large text, centered."""

    def construct(self) -> None:
        self.statement = self.data.get("statement", "")
        self.emphasis_word = self.data.get("emphasis_word", "")
