"""Unit tests for the Bull vs Bear Projection effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.bull_bear_projection import (
    InsufficientDataError,
    compute_projection,
    generate,
)


class TestComputeProjection:
    def test_zero_rate(self):
        result = compute_projection(100, 0.0, 3)
        assert result == [100, 100, 100, 100]

    def test_positive_rate(self):
        result = compute_projection(100, 0.10, 2)
        assert len(result) == 3
        assert abs(result[1] - 110.0) < 0.01
        assert abs(result[2] - 121.0) < 0.01

    def test_negative_rate(self):
        result = compute_projection(100, -0.20, 1)
        assert abs(result[1] - 80.0) < 0.01

    def test_zero_years(self):
        result = compute_projection(100, 0.10, 0)
        assert result == [100]

    def test_first_element_is_last_price(self):
        result = compute_projection(42.5, 0.25, 3)
        assert result[0] == 42.5


class TestInsufficientDataError:
    def test_error_message(self):
        err = InsufficientDataError(1)
        assert "2" in str(err)
        assert "1" in str(err)
        assert err.count == 1

    def test_zero_count(self):
        err = InsufficientDataError(0)
        assert err.count == 0


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100 + i * 5 for i in range(12)],
            "optimistic_rate": 0.25,
            "realistic_rate": 0.10,
            "pessimistic_rate": -0.15,
            "projection_years": 3,
            "projection_labels": ["Bull", "Base", "Bear"],
        }
        data.update(overrides)
        return {"data": data, "title": "AAPL Projection"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "BullBearProjectionScene" in generate(self._make_instruction())

    def test_dashed_line_present(self):
        code = generate(self._make_instruction())
        assert "DashedLine" in code

    def test_today_marker(self):
        code = generate(self._make_instruction())
        assert "Today" in code

    def test_projection_labels_in_output(self):
        code = generate(self._make_instruction())
        assert "Bull" in code
        assert "Base" in code
        assert "Bear" in code

    def test_custom_labels(self):
        code = generate(self._make_instruction(projection_labels=["Up", "Flat", "Down"]))
        assert "Up" in code
        assert "Flat" in code
        assert "Down" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_insufficient_data_renders_error_text(self):
        code = generate({"data": {"values": [100]}})
        ast.parse(code)
        assert "Insufficient" in code
