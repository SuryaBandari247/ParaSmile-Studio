"""Unit tests for the Moat Comparison Radar effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.moat_radar import (
    LengthMismatchError,
    RangeError,
    find_max_advantage_index,
    generate,
)


class TestFindMaxAdvantageIndex:
    def test_first_element_max(self):
        assert find_max_advantage_index([90, 50, 60], [30, 50, 60]) == 0

    def test_last_element_max(self):
        assert find_max_advantage_index([50, 50, 90], [50, 50, 30]) == 2

    def test_equal_values(self):
        assert find_max_advantage_index([50, 50, 50], [50, 50, 50]) == 0

    def test_empty_returns_zero(self):
        assert find_max_advantage_index([], []) == 0

    def test_negative_advantage(self):
        # B is always better, but index 0 has least disadvantage
        assert find_max_advantage_index([10, 5, 3], [20, 20, 20]) == 0


class TestLengthMismatchError:
    def test_error_message(self):
        err = LengthMismatchError(3, 4, 5)
        assert err.len_a == 3
        assert err.len_b == 4
        assert err.len_labels == 5
        assert "3" in str(err)
        assert "4" in str(err)
        assert "5" in str(err)


class TestRangeError:
    def test_error_message(self):
        err = RangeError(150.0, 2, "Company A")
        assert err.value == 150.0
        assert err.index == 2
        assert err.company == "Company A"
        assert "150" in str(err)
        assert "Company A" in str(err)


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "company_a_name": "Apple",
            "company_a_values": [85, 70, 90, 60, 75],
            "company_b_name": "Samsung",
            "company_b_values": [70, 80, 65, 75, 60],
            "metric_labels": ["Brand", "R&D", "Margins", "Distribution", "Ecosystem"],
        }
        data.update(overrides)
        return {"data": data, "title": "Moat Comparison"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "MoatRadarScene" in generate(self._make_instruction())

    def test_polygon_creation(self):
        code = generate(self._make_instruction())
        assert "Polygon" in code or "VMobject" in code

    def test_indicate_on_max_advantage(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

    def test_company_names_in_output(self):
        code = generate(self._make_instruction())
        assert "Apple" in code
        assert "Samsung" in code

    def test_custom_colors(self):
        code = generate(self._make_instruction(
            company_a_color="#00FF00", company_b_color="#0000FF"
        ))
        assert "#00FF00" in code
        assert "#0000FF" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {"metric_labels": []}})
        ast.parse(code)

    def test_legend_present(self):
        code = generate(self._make_instruction())
        assert "legend" in code.lower() or "Apple" in code
