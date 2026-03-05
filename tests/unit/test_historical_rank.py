"""Unit tests for the Historical Rank effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.historical_rank import (
    InsufficientDataError,
    compute_percentile,
    DEFAULT_BANDS,
    generate,
)


class TestComputePercentile:
    def test_median_value(self):
        historical = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        pct = compute_percentile(55, historical)
        assert abs(pct - 50.0) < 0.01

    def test_lowest_value(self):
        historical = [10, 20, 30, 40, 50]
        pct = compute_percentile(5, historical)
        assert pct == 0.0

    def test_highest_value(self):
        historical = [10, 20, 30, 40, 50]
        pct = compute_percentile(100, historical)
        assert pct == 100.0

    def test_empty_historical(self):
        assert compute_percentile(50, []) == 0.0

    def test_all_same_values(self):
        historical = [50, 50, 50, 50, 50]
        pct = compute_percentile(50, historical)
        assert pct == 0.0  # none are strictly less

    def test_exact_match(self):
        historical = [10, 20, 30, 40, 50]
        pct = compute_percentile(30, historical)
        # 2 values below 30 (10, 20) out of 5
        assert abs(pct - 40.0) < 0.01


class TestInsufficientDataError:
    def test_error_message(self):
        err = InsufficientDataError(5)
        assert "10" in str(err)
        assert "5" in str(err)
        assert err.count == 5


class TestDefaultBands:
    def test_four_bands(self):
        assert len(DEFAULT_BANDS) == 4

    def test_ascending_percentiles(self):
        pcts = [b["pct"] for b in DEFAULT_BANDS]
        assert pcts == sorted(pcts)


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "current_value": 28.5,
            "historical_values": [15, 18, 20, 22, 24, 25, 26, 27, 28, 30, 32, 35, 38, 40],
            "metric_label": "P/E Ratio",
        }
        data.update(overrides)
        return {"data": data, "title": "Historical Valuation"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "HistoricalRankScene" in generate(self._make_instruction())

    def test_metric_label_in_output(self):
        code = generate(self._make_instruction())
        assert "P/E Ratio" in code

    def test_percentile_bands_drawn(self):
        code = generate(self._make_instruction())
        assert "Rectangle" in code

    def test_marker_animation(self):
        code = generate(self._make_instruction())
        assert "Triangle" in code

    def test_indicate_marker(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

    def test_band_labels(self):
        code = generate(self._make_instruction())
        assert "Cheap" in code
        assert "Expensive" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_insufficient_data_renders_error(self):
        code = generate({"data": {"historical_values": [1, 2, 3]}})
        ast.parse(code)
        assert "Insufficient" in code

    def test_custom_bands(self):
        code = generate(self._make_instruction(percentile_bands=[
            {"label": "Low", "pct": 30},
            {"label": "High", "pct": 70},
        ]))
        ast.parse(code)
        assert "Low" in code
        assert "High" in code

    def test_value_display(self):
        code = generate(self._make_instruction())
        assert "percentile" in code.lower()

    def test_ladder_structure(self):
        code = generate(self._make_instruction())
        assert "Line" in code or "bar" in code
