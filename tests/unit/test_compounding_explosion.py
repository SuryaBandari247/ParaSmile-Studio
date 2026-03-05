"""Unit tests for the Compounding Explosion effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.compounding_explosion import (
    RangeError,
    compute_curve,
    find_breakpoint,
    generate,
)


class TestComputeCurve:
    def test_zero_rate(self):
        result = compute_curve(100, 0.0, 5)
        assert all(abs(v - 100) < 0.01 for v in result)
        assert len(result) == 6

    def test_positive_rate(self):
        result = compute_curve(100, 0.10, 3)
        assert len(result) == 4
        assert abs(result[0] - 100) < 0.01
        assert abs(result[1] - 110) < 0.01
        assert abs(result[2] - 121) < 0.01
        assert abs(result[3] - 133.1) < 0.1

    def test_single_year(self):
        result = compute_curve(1000, 0.05, 0)
        assert result == [1000]

    def test_compound_formula(self):
        result = compute_curve(50, 0.20, 5)
        for y, v in enumerate(result):
            expected = 50 * (1.20 ** y)
            assert abs(v - expected) < 0.01


class TestFindBreakpoint:
    def test_doubling(self):
        values = [100, 110, 121, 133, 146, 161, 177, 195, 214]
        bp = find_breakpoint(values, threshold_ratio=2.0)
        assert values[bp] >= 200

    def test_no_doubling(self):
        values = [100, 105, 110]
        bp = find_breakpoint(values, threshold_ratio=2.0)
        assert bp == len(values) - 1

    def test_empty_values(self):
        assert find_breakpoint([], 2.0) == 0

    def test_immediate_doubling(self):
        values = [100, 250]
        bp = find_breakpoint(values, 2.0)
        assert bp == 1


class TestRangeError:
    def test_error_message(self):
        err = RangeError(-0.5, "rate")
        assert "-0.5" in str(err)
        assert err.value == -0.5
        assert err.field == "rate"


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "principal": 10000,
            "rate": 0.10,
            "years": 20,
            "explosion_color": "#FFD700",
            "line_color": "#FFFFFF",
            "show_doubling_markers": True,
        }
        data.update(overrides)
        return {"data": data, "title": "Compounding Growth"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "CompoundingExplosionScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_explosion_color_in_output(self):
        code = generate(self._make_instruction())
        assert "#FFD700" in code

    def test_doubling_markers(self):
        code = generate(self._make_instruction())
        assert "DashedLine" in code or "2x" in code

    def test_breakpoint_glow(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

    def test_custom_breakpoint(self):
        code = generate(self._make_instruction(breakpoint_year=10))
        ast.parse(code)

    def test_invalid_rate_renders_error(self):
        code = generate(self._make_instruction(rate=-0.1))
        ast.parse(code)
        assert "Invalid" in code

    def test_invalid_years_renders_error(self):
        code = generate(self._make_instruction(years=1))
        ast.parse(code)
        assert "Invalid" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_end_badge(self):
        code = generate(self._make_instruction())
        assert "badge" in code

    def test_no_doubling_markers(self):
        code = generate(self._make_instruction(show_doubling_markers=False))
        ast.parse(code)
