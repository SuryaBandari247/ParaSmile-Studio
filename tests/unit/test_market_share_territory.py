"""Unit tests for the Market Share Territory effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.market_share_territory import (
    InsufficientDataError,
    find_crossover_indices,
    territory_owner,
    generate,
)


class TestFindCrossoverIndices:
    def test_single_crossover(self):
        a = [10, 20, 30]
        b = [15, 15, 35]
        crossovers = find_crossover_indices(a, b)
        # a < b at 0, a >= b at 1, a < b at 2 → crossovers at 1 and 2
        assert 1 in crossovers
        assert 2 in crossovers

    def test_no_crossover(self):
        a = [10, 20, 30]
        b = [5, 10, 15]
        assert find_crossover_indices(a, b) == []

    def test_empty_series(self):
        assert find_crossover_indices([], []) == []

    def test_single_point(self):
        assert find_crossover_indices([10], [5]) == []

    def test_mismatched_lengths(self):
        a = [10, 20, 30, 40]
        b = [5, 25]
        crossovers = find_crossover_indices(a, b)
        assert 1 in crossovers


class TestTerritoryOwner:
    def test_a_higher(self):
        assert territory_owner(100, 50) == "a"

    def test_b_higher(self):
        assert territory_owner(50, 100) == "b"

    def test_equal(self):
        assert territory_owner(100, 100) == "a"


class TestInsufficientDataError:
    def test_error_message(self):
        err = InsufficientDataError(1)
        assert "2" in str(err)
        assert err.count == 1


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "series": [
                {
                    "name": "TSMC",
                    "data": [
                        {"date": "2024-01-01", "value": 55},
                        {"date": "2024-04-01", "value": 58},
                        {"date": "2024-07-01", "value": 52},
                        {"date": "2024-10-01", "value": 60},
                    ],
                    "territory_color": "#58a6ff",
                },
                {
                    "name": "Samsung",
                    "data": [
                        {"date": "2024-01-01", "value": 45},
                        {"date": "2024-04-01", "value": 50},
                        {"date": "2024-07-01", "value": 54},
                        {"date": "2024-10-01", "value": 48},
                    ],
                    "territory_color": "#f97583",
                },
            ],
            "fill_opacity": 0.3,
        }
        data.update(overrides)
        return {"data": data, "title": "Market Share"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "MarketShareTerritoryScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_series_names_in_output(self):
        code = generate(self._make_instruction())
        assert "TSMC" in code
        assert "Samsung" in code

    def test_territory_fills(self):
        code = generate(self._make_instruction())
        assert "Polygon" in code

    def test_legend(self):
        code = generate(self._make_instruction())
        assert "legend" in code.lower() or "Dot" in code

    def test_lines_drawn(self):
        code = generate(self._make_instruction())
        assert "line_a" in code or "VMobject" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_single_series_renders_error(self):
        code = generate({"data": {"series": [{"name": "A", "data": [{"date": "2024-01-01", "value": 10}], "territory_color": "#fff"}]}})
        ast.parse(code)
        assert "2 series" in code

    def test_insufficient_data_renders_error(self):
        code = generate({"data": {"series": [
            {"name": "A", "data": [{"date": "2024-01-01", "value": 10}], "territory_color": "#fff"},
            {"name": "B", "data": [{"date": "2024-01-01", "value": 20}], "territory_color": "#aaa"},
        ]}})
        ast.parse(code)
        assert "Insufficient" in code

    def test_custom_fill_opacity(self):
        code = generate(self._make_instruction(fill_opacity=0.6))
        ast.parse(code)
        assert "0.6" in code

    def test_territory_colors_in_output(self):
        code = generate(self._make_instruction())
        assert "#58a6ff" in code
        assert "#f97583" in code
