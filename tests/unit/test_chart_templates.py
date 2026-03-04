"""Unit tests for BarChartScene in asset_orchestrator.chart_templates."""

import pytest

from asset_orchestrator.chart_templates import (
    BACKGROUND_COLOR,
    TEXT_COLOR,
    BarChartScene,
    _group_categories,
    _truncate_title,
)
from asset_orchestrator.scene_registry import BaseScene


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(n: int) -> dict:
    """Return a data dict with *n* categories."""
    return {
        "labels": [f"cat_{i}" for i in range(n)],
        "values": list(range(1, n + 1)),
    }


# ---------------------------------------------------------------------------
# BaseScene subclass check
# ---------------------------------------------------------------------------

class TestBarChartSceneInheritance:
    def test_is_subclass_of_base_scene(self):
        assert issubclass(BarChartScene, BaseScene)

    def test_instance_is_base_scene(self):
        scene = BarChartScene(title="T", data={"labels": ["a"], "values": [1]})
        assert isinstance(scene, BaseScene)


# ---------------------------------------------------------------------------
# Title truncation
# ---------------------------------------------------------------------------

class TestTitleTruncation:
    def test_title_exactly_60_chars_not_truncated(self):
        title = "A" * 60
        assert _truncate_title(title) == title

    def test_title_61_chars_truncated(self):
        title = "A" * 61
        result = _truncate_title(title)
        assert result == "A" * 60 + "..."
        assert len(result) == 63  # 60 + "..."

    def test_short_title_unchanged(self):
        assert _truncate_title("Hello") == "Hello"

    def test_empty_title(self):
        assert _truncate_title("") == ""

    def test_construct_stores_truncated_title(self):
        scene = BarChartScene(title="X" * 100, data={"labels": ["a"], "values": [1]})
        scene.construct()
        assert scene.processed_title == "X" * 60 + "..."


# ---------------------------------------------------------------------------
# Category grouping
# ---------------------------------------------------------------------------

class TestCategoryGrouping:
    def test_10_categories_no_grouping(self):
        labels, values = _group_categories(list("abcdefghij"), list(range(10)))
        assert len(labels) == 10
        assert "Other" not in labels

    def test_11_categories_triggers_grouping(self):
        raw_labels = [f"c{i}" for i in range(11)]
        raw_values = list(range(11))
        labels, values = _group_categories(raw_labels, raw_values)
        assert len(labels) == 11  # top 10 + Other
        assert labels[-1] == "Other"

    def test_other_value_equals_sum_of_grouped(self):
        raw_labels = [f"c{i}" for i in range(15)]
        raw_values = list(range(1, 16))  # 1..15
        labels, values = _group_categories(raw_labels, raw_values)
        # Top 10 by value: 15,14,...,6  — grouped: 5,4,3,2,1 → sum = 15
        assert values[-1] == sum(range(1, 6))
        assert labels[-1] == "Other"

    def test_empty_data(self):
        labels, values = _group_categories([], [])
        assert labels == []
        assert values == []

    def test_construct_stores_grouped_data(self):
        data = _make_data(12)
        scene = BarChartScene(title="T", data=data)
        scene.construct()
        assert len(scene.processed_data["labels"]) == 11
        assert scene.processed_data["labels"][-1] == "Other"


# ---------------------------------------------------------------------------
# Construct — colour scheme & bars
# ---------------------------------------------------------------------------

class TestConstruct:
    def test_background_color(self):
        scene = BarChartScene(title="T", data=_make_data(3))
        scene.construct()
        assert scene.background_color == BACKGROUND_COLOR

    def test_text_color(self):
        scene = BarChartScene(title="T", data=_make_data(3))
        scene.construct()
        assert scene.text_color == TEXT_COLOR

    def test_bars_match_data(self):
        data = {"labels": ["A", "B", "C"], "values": [10, 20, 30]}
        scene = BarChartScene(title="T", data=data)
        scene.construct()
        assert len(scene.bars) == 3
        assert scene.bars[0]["label"] == "A"
        assert scene.bars[0]["value"] == 10
        assert scene.bars[0]["value_label"] == "10"

    def test_each_bar_has_accent_color(self):
        scene = BarChartScene(title="T", data=_make_data(5))
        scene.construct()
        for bar in scene.bars:
            assert bar["color"].startswith("#")

    def test_axes_config_y_range(self):
        data = {"labels": ["X"], "values": [42]}
        scene = BarChartScene(title="T", data=data)
        scene.construct()
        assert scene.axes_config["y_range"] == [0, 42]

    def test_axes_config_x_labels(self):
        data = {"labels": ["X", "Y"], "values": [1, 2]}
        scene = BarChartScene(title="T", data=data)
        scene.construct()
        assert scene.axes_config["x_labels"] == ["X", "Y"]

    def test_style_passed_through(self):
        style = {"font_size": 24}
        scene = BarChartScene(title="T", data=_make_data(2), style=style)
        assert scene.style == style
