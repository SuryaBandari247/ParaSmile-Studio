"""Scene Registry — maps instruction type strings to Scene classes."""

from __future__ import annotations

from asset_orchestrator.exceptions import DuplicateSceneTypeError, UnknownSceneTypeError


class BaseScene:
    """Lightweight base class for all scene types.

    Acts as a stand-in for Manim's Scene so the registry and mapper can work
    without requiring Manim to be installed.  Concrete scene classes in
    chart_templates, code_snippet_scene, and text_overlay_scene subclass this.
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        self.title = title
        self.data = data or {}
        self.style = style

    def construct(self) -> None:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class SceneRegistry:
    """Maps instruction type strings to Scene classes."""

    def __init__(self) -> None:
        """Initialize with built-in scene types.

        Imports are deferred to avoid circular dependencies — the scene
        modules import ``BaseScene`` from this file.
        """
        from asset_orchestrator.chart_templates import (
            BarChartScene,
            LineChartScene,
            PieChartScene,
        )
        from asset_orchestrator.code_snippet_scene import CodeSnippetScene
        from asset_orchestrator.text_overlay_scene import TextOverlayScene
        from asset_orchestrator.youtube_scenes import (
            BulletRevealScene,
            ComparisonScene,
            FullscreenStatementScene,
            QuoteBlockScene,
            RedditPostScene,
            SectionTitleScene,
            StatCalloutScene,
        )
        from asset_orchestrator.stock_scenes import (
            StockVideoScene,
            StockWithTextScene,
            StockWithStatScene,
            StockQuoteScene,
        )

        self._registry: dict[str, type] = {
            "bar_chart": BarChartScene,
            "line_chart": LineChartScene,
            "pie_chart": PieChartScene,
            "code_snippet": CodeSnippetScene,
            "text_overlay": TextOverlayScene,
            "reddit_post": RedditPostScene,
            "stat_callout": StatCalloutScene,
            "quote_block": QuoteBlockScene,
            "section_title": SectionTitleScene,
            "bullet_reveal": BulletRevealScene,
            "comparison": ComparisonScene,
            "fullscreen_statement": FullscreenStatementScene,
            "stock_video": StockVideoScene,
            "stock_with_text": StockWithTextScene,
            "stock_with_stat": StockWithStatScene,
            "stock_quote": StockQuoteScene,
            # Data chart types — routed through Manim codegen
            "data_chart": BarChartScene,
            "timeseries": LineChartScene,
            "horizontal_bar": BarChartScene,
            "grouped_bar": BarChartScene,
            "donut": PieChartScene,
        }

    def get(self, type_key: str) -> type:
        """Look up a Scene class by type key.

        Args:
            type_key: Instruction type string (e.g. ``"bar_chart"``).

        Returns:
            The Scene class registered under *type_key*.

        Raises:
            UnknownSceneTypeError: If *type_key* is not registered.
        """
        if type_key not in self._registry:
            raise UnknownSceneTypeError(type_key, list(self._registry.keys()))
        return self._registry[type_key]

    def register(self, type_key: str, scene_class: type) -> None:
        """Register a new scene type at runtime.

        Args:
            type_key: Instruction type string.
            scene_class: Scene class to associate with *type_key*.

        Raises:
            DuplicateSceneTypeError: If *type_key* is already registered.
        """
        if type_key in self._registry:
            raise DuplicateSceneTypeError(type_key)
        self._registry[type_key] = scene_class

    def list_types(self) -> list[str]:
        """Return all registered type keys."""
        return list(self._registry.keys())
