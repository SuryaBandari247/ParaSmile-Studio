"""Unit tests for the Momentum Glow effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.momentum_glow import (
    InsufficientDataError,
    compute_rolling_slope,
    generate,
)


class TestComputeRollingSlope:
    def test_basic_slope(self):
        values = [0, 1, 2, 3, 4]
        slopes = compute_rolling_slope(values, 2)
        assert len(slopes) == 5
        # slope at index 2 = (2 - 0) / 2 = 1.0
        assert abs(slopes[2] - 1.0) < 0.01

    def test_flat_series(self):
        values = [10, 10, 10, 10]
        slopes = compute_rolling_slope(values, 2)
        for s in slopes[2:]:
            assert abs(s) < 0.01

    def test_window_larger_than_data(self):
        values = [1, 2]
        slopes = compute_rolling_slope(values, 5)
        assert all(s == 0.0 for s in slopes)

    def test_returns_correct_length(self):
        values = list(range(20))
        slopes = compute_rolling_slope(values, 5)
        assert len(slopes) == 20


class TestInsufficientDataError:
    def test_error_message(self):
        err = InsufficientDataError(5, 20)
        assert "20" in str(err)
        assert "5" in str(err)
        assert err.count == 5
        assert err.window == 20


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100, 102, 108, 115, 130, 128, 120, 118, 125, 140, 155, 160],
            "momentum_window": 3,
            "glow_color_up": "#00FFAA",
            "glow_color_down": "#FF453A",
        }
        data.update(overrides)
        return {"data": data, "title": "Momentum Test"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "MomentumGlowScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_glow_colors_in_output(self):
        code = generate(self._make_instruction())
        assert "#00FFAA" in code
        assert "#FF453A" in code

    def test_segments_drawn(self):
        code = generate(self._make_instruction())
        assert "segments" in code or "Line" in code

    def test_end_badge(self):
        code = generate(self._make_instruction())
        assert "badge" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_insufficient_data_renders_error(self):
        code = generate({"data": {"values": [100]}})
        ast.parse(code)
        assert "Insufficient" in code

    def test_series_fallback(self):
        instruction = {
            "data": {
                "series": [{"data": [
                    {"date": "2024-01-01", "value": 100},
                    {"date": "2024-02-01", "value": 120},
                    {"date": "2024-03-01", "value": 140},
                ]}],
                "momentum_window": 2,
            },
            "title": "Test",
        }
        code = generate(instruction)
        ast.parse(code)

    def test_custom_threshold(self):
        code = generate(self._make_instruction(glow_threshold_sigma=2.0))
        ast.parse(code)
        assert "2.0" in code

    def test_lagged_start_animation(self):
        code = generate(self._make_instruction())
        assert "LaggedStart" in code
