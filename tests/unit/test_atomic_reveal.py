"""Unit tests for the Atomic Component Reveal effect."""

from __future__ import annotations

import ast
import math

import pytest

from effects_catalog.templates.atomic_reveal import (
    SENTIMENT_COLORS,
    ComponentNotFoundError,
    compute_grid_positions,
    compute_radial_positions,
    generate,
)


class TestComputeRadialPositions:
    def test_single_component(self):
        positions = compute_radial_positions(1)
        assert len(positions) == 1

    def test_four_components_symmetry(self):
        positions = compute_radial_positions(4, radius=2.0)
        assert len(positions) == 4
        # All should be at distance 2.0 from origin
        for x, y in positions:
            assert abs(math.sqrt(x**2 + y**2) - 2.0) < 0.01

    def test_zero_components(self):
        assert compute_radial_positions(0) == []


class TestComputeGridPositions:
    def test_single_component(self):
        positions = compute_grid_positions(1)
        assert len(positions) == 1
        assert positions[0] == (0.0, 0.0)

    def test_four_components(self):
        positions = compute_grid_positions(4)
        assert len(positions) == 4

    def test_zero_components(self):
        assert compute_grid_positions(0) == []


class TestComponentNotFoundError:
    def test_error_message(self):
        err = ComponentNotFoundError("Revenue", ["Margins", "Debt", "Growth"])
        assert err.name == "Revenue"
        assert "Revenue" in str(err)
        assert err.available == ["Margins", "Debt", "Growth"]


class TestSentimentColors:
    def test_positive_is_green(self):
        assert SENTIMENT_COLORS["positive"] == "#26A69A"

    def test_negative_is_red(self):
        assert SENTIMENT_COLORS["negative"] == "#EF5350"

    def test_neutral_is_grey(self):
        assert SENTIMENT_COLORS["neutral"] == "#787B86"


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "entity_name": "NVIDIA",
            "components": [
                {"name": "Data Center", "value": "$22.6B", "sentiment": "positive"},
                {"name": "Gaming", "value": "$2.9B", "sentiment": "neutral"},
                {"name": "Auto", "value": "$0.3B", "sentiment": "negative"},
                {"name": "Pro Viz", "value": "$0.4B", "sentiment": "neutral"},
            ],
            "highlight_component": "Data Center",
            "layout": "radial",
        }
        data.update(overrides)
        return {"data": data, "title": "NVDA Revenue Breakdown"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "AtomicRevealScene" in generate(self._make_instruction())

    def test_lagged_start_present(self):
        code = generate(self._make_instruction())
        assert "LaggedStart" in code

    def test_sentiment_colors_in_output(self):
        code = generate(self._make_instruction())
        assert "#26A69A" in code  # positive
        assert "#EF5350" in code  # negative

    def test_highlight_indicate(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

    def test_grid_layout_valid_python(self):
        code = generate(self._make_instruction(layout="grid"))
        ast.parse(code)
        assert "grid" in code

    def test_radial_layout(self):
        code = generate(self._make_instruction(layout="radial"))
        ast.parse(code)

    def test_empty_components_valid_python(self):
        code = generate({"data": {"entity_name": "Test", "components": []}})
        ast.parse(code)

    def test_entity_name_in_output(self):
        code = generate(self._make_instruction())
        assert "NVIDIA" in code
