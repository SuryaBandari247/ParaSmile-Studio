"""Unit tests for the Relative Velocity Comparison effect."""

from __future__ import annotations

import ast

from effects_catalog.templates.relative_velocity import (
    compute_overlap,
    compute_spread,
    generate,
)


class TestComputeOverlap:
    def test_full_overlap(self):
        assert compute_overlap(["a", "b", "c"], ["a", "b", "c"]) == ["a", "b", "c"]

    def test_partial_overlap(self):
        assert compute_overlap(["a", "b", "c"], ["b", "c", "d"]) == ["b", "c"]

    def test_no_overlap(self):
        assert compute_overlap(["a", "b"], ["c", "d"]) == []

    def test_empty(self):
        assert compute_overlap([], ["a"]) == []


class TestComputeSpread:
    def test_equal_values(self):
        assert compute_spread(100, 100) == 0.0

    def test_positive_spread(self):
        spread = compute_spread(120, 100)
        assert abs(spread - 20.0) < 0.01

    def test_zero_base(self):
        assert compute_spread(100, 0) == 0.0


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "series_a_name": "NVDA",
            "series_b_name": "AMD",
            "values_a": [100, 120, 140, 160, 180],
            "values_b": [100, 110, 105, 115, 125],
            "dates": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05"],
        }
        data.update(overrides)
        return {"data": data, "title": "GPU Wars"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "RelativeVelocityScene" in generate(self._make_instruction())

    def test_arrow_present(self):
        assert "Arrow" in generate(self._make_instruction())

    def test_custom_arrow_color(self):
        code = generate(self._make_instruction(arrow_color="#00FF00"))
        assert "#00FF00" in code

    def test_delta_arrow_disabled(self):
        code = generate(self._make_instruction(show_delta_arrow=False))
        ast.parse(code)

    def test_empty_data(self):
        code = generate({"data": {"series_a_name": "A", "series_b_name": "B"}})
        ast.parse(code)

    def test_legend_present(self):
        code = generate(self._make_instruction())
        assert "NVDA" in code and "AMD" in code
