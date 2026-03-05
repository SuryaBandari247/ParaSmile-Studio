"""Unit tests for the Forensic Zoom effect template."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.forensic_zoom import (
    DateRangeError,
    generate,
)


class TestGenerate:
    """Tests for Forensic Zoom Manim code generation."""

    def _make_instruction(self, **overrides):
        data = {
            "focus_date": "2024-08-05",
            "focus_window_days": 30,
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100 + i * 5 for i in range(12)],
            "events": [{"date": "2024-08-05", "label": "Crash"}],
        }
        data.update(overrides)
        return {"data": data, "title": "NVDA Forensic Zoom"}

    def test_generates_valid_python(self):
        code = generate(self._make_instruction())
        ast.parse(code)

    def test_contains_scene_class(self):
        code = generate(self._make_instruction())
        assert "class ForensicZoomScene(MovingCameraScene)" in code

    def test_jump_cut_mode(self):
        code = generate(self._make_instruction(zoom_mode="jump_cut"))
        ast.parse(code)
        assert "jump_cut" in code

    def test_travel_mode(self):
        code = generate(self._make_instruction(zoom_mode="travel"))
        ast.parse(code)
        assert "travel" in code

    def test_custom_glow_color(self):
        code = generate(self._make_instruction(glow_color="#00FF00"))
        assert "#00FF00" in code

    def test_custom_blur_opacity(self):
        code = generate(self._make_instruction(blur_opacity=0.3))
        assert "0.3" in code

    def test_wide_hold_parameter(self):
        code = generate(self._make_instruction(wide_hold=2.5))
        assert "2.5" in code

    def test_events_included(self):
        code = generate(self._make_instruction())
        assert "Crash" in code

    def test_empty_data_still_valid_python(self):
        """Even with no dates/values, generated code should be parseable."""
        code = generate({"data": {"focus_date": "2024-01-01", "dates": [], "values": []}})
        ast.parse(code)

    def test_surrounding_rectangle_present(self):
        code = generate(self._make_instruction())
        assert "SurroundingRectangle" in code

    def test_indicate_present(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

    def test_focus_window_days_default(self):
        """Default focus_window_days should be 30."""
        code = generate({"data": {"focus_date": "2024-06-01"}})
        assert "30" in code


class TestDateRangeError:
    """Tests for the DateRangeError exception."""

    def test_error_message(self):
        err = DateRangeError("2024-01-01", "2024-06-01", "2024-12-31")
        assert "2024-01-01" in str(err)
        assert "2024-06-01" in str(err)
        assert "2024-12-31" in str(err)

    def test_attributes(self):
        err = DateRangeError("2024-01-01", "2024-06-01", "2024-12-31")
        assert err.focus_date == "2024-01-01"
        assert err.valid_start == "2024-06-01"
        assert err.valid_end == "2024-12-31"
