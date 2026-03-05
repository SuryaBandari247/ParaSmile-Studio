"""Unit tests for the Speed Ramp effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.speed_ramp import (
    DateOrderError,
    RangeError,
    compute_segment_durations,
    generate,
)


class TestDateOrderError:
    def test_error_message(self):
        err = DateOrderError("2024-06-01", "2024-01-01")
        assert "2024-06-01" in str(err)
        assert err.start == "2024-06-01"
        assert err.end == "2024-01-01"


class TestRangeError:
    def test_error_message(self):
        err = RangeError(-1.0)
        assert "-1.0" in str(err)
        assert err.speed == -1.0

    def test_zero_speed(self):
        err = RangeError(0.0)
        assert err.speed == 0.0


class TestComputeSegmentDurations:
    def test_basic_uniform(self):
        durations = compute_segment_durations(5, [], [], base_duration=2.0)
        assert len(durations) == 4
        assert all(abs(d - 0.5) < 0.01 for d in durations)

    def test_speed_multiplier_applied(self):
        dates = ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]
        regimes = [{"start": "2024-01-01", "end": "2024-02-01", "speed": 2.0}]
        durations = compute_segment_durations(4, regimes, dates, base_duration=3.0)
        # First segment should be halved
        assert durations[0] < durations[2]

    def test_zero_speed_ignored(self):
        dates = ["2024-01-01", "2024-02-01"]
        regimes = [{"start": "2024-01-01", "end": "2024-02-01", "speed": 0.0}]
        durations = compute_segment_durations(2, regimes, dates)
        assert len(durations) == 1

    def test_single_point(self):
        durations = compute_segment_durations(1, [], [])
        assert len(durations) == 0


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100, 105, 110, 85, 80, 90, 95, 100, 108, 115, 120, 125],
            "speed_regimes": [
                {"start": "2024-01-01", "end": "2024-03-01", "speed": 3.0},
                {"start": "2024-04-01", "end": "2024-06-01", "speed": 0.3},
            ],
            "transition_frames": 10,
        }
        data.update(overrides)
        return {"data": data, "title": "Speed Ramp Test"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "SpeedRampScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_speed_regimes_in_output(self):
        code = generate(self._make_instruction())
        assert "speed_regimes" in code

    def test_segment_drawing(self):
        code = generate(self._make_instruction())
        assert "Line" in code

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

    def test_no_speed_regimes(self):
        code = generate(self._make_instruction(speed_regimes=[]))
        ast.parse(code)

    def test_series_fallback(self):
        instruction = {
            "data": {
                "series": [{"data": [
                    {"date": "2024-01-01", "value": 100},
                    {"date": "2024-06-01", "value": 120},
                ]}],
                "speed_regimes": [],
            },
            "title": "Test",
        }
        code = generate(instruction)
        ast.parse(code)

    def test_custom_transition_frames(self):
        code = generate(self._make_instruction(transition_frames=20))
        ast.parse(code)
        assert "20" in code
