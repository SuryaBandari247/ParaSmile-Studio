"""Unit tests for the Contextual Heatmap effect."""

from __future__ import annotations

import ast

from effects_catalog.templates.contextual_heatmap import (
    TickerResolutionError,
    assign_heatmap_color,
    generate,
)


class TestAssignHeatmapColor:
    def test_above_start_returns_green(self):
        assert assign_heatmap_color(110, 100, "#00E676", "#FF453A") == "#00E676"

    def test_below_start_returns_red(self):
        assert assign_heatmap_color(90, 100, "#00E676", "#FF453A") == "#FF453A"

    def test_equal_to_start_returns_green(self):
        assert assign_heatmap_color(100, 100, "#00E676", "#FF453A") == "#00E676"


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "benchmark_ticker": "^GSPC",
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [150 + i * 3 for i in range(12)],
            "benchmark_values": [4500 + i * 50 for i in range(12)],
        }
        data.update(overrides)
        return {"data": data, "title": "AAPL vs S&P 500"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "ContextualHeatmapScene" in generate(self._make_instruction())

    def test_custom_colors(self):
        code = generate(self._make_instruction(green_color="#00FF00", red_color="#FF0000"))
        assert "#00FF00" in code
        assert "#FF0000" in code

    def test_benchmark_label(self):
        code = generate(self._make_instruction(benchmark_label="Nasdaq"))
        assert "Nasdaq" in code

    def test_empty_data(self):
        code = generate({"data": {"benchmark_ticker": "^GSPC"}})
        ast.parse(code)


class TestTickerResolutionError:
    def test_error_message(self):
        err = TickerResolutionError("INVALID")
        assert "INVALID" in str(err)
        assert err.ticker == "INVALID"
