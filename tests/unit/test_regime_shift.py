"""Unit tests for the Regime Shift effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.regime_shift import (
    DateOrderError,
    DateRangeError,
    generate,
)


class TestDateOrderError:
    def test_error_message(self):
        err = DateOrderError("2024-06-01", "2024-01-01")
        assert "2024-06-01" in str(err)
        assert "2024-01-01" in str(err)
        assert err.start == "2024-06-01"
        assert err.end == "2024-01-01"


class TestDateRangeError:
    def test_error_message(self):
        err = DateRangeError("QE Era", "2024-01-01", "2024-12-01")
        assert "QE Era" in str(err)
        assert err.regime_label == "QE Era"
        assert err.data_start == "2024-01-01"
        assert err.data_end == "2024-12-01"


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100, 105, 110, 85, 90, 95, 100, 108, 115, 120, 118, 125],
            "regimes": [
                {"start": "2024-01-01", "end": "2024-03-01", "label": "Bull Run", "color": "#3fb950"},
                {"start": "2024-04-01", "end": "2024-06-01", "label": "Correction", "color": "#f85149"},
                {"start": "2024-07-01", "end": "2024-12-01", "label": "Recovery", "color": "#58a6ff"},
            ],
            "zone_opacity": 0.15,
        }
        data.update(overrides)
        return {"data": data, "title": "Market Regimes"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "RegimeShiftScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_regime_labels_in_output(self):
        code = generate(self._make_instruction())
        assert "Bull Run" in code
        assert "Correction" in code
        assert "Recovery" in code

    def test_zone_opacity(self):
        code = generate(self._make_instruction())
        assert "zone_opacity" in code

    def test_rectangle_zones(self):
        code = generate(self._make_instruction())
        assert "Rectangle" in code

    def test_sequential_zone_reveal(self):
        code = generate(self._make_instruction())
        assert "FadeIn" in code

    def test_price_line_drawn(self):
        code = generate(self._make_instruction())
        assert "line" in code.lower()

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_insufficient_data_renders_error(self):
        code = generate({"data": {"values": [100]}})
        ast.parse(code)
        assert "Insufficient" in code

    def test_no_regimes(self):
        code = generate(self._make_instruction(regimes=[]))
        ast.parse(code)

    def test_end_badge(self):
        code = generate(self._make_instruction())
        assert "badge" in code

    def test_series_fallback(self):
        instruction = {
            "data": {
                "series": [{"data": [
                    {"date": "2024-01-01", "value": 100},
                    {"date": "2024-06-01", "value": 120},
                ]}],
                "regimes": [{"start": "2024-01-01", "end": "2024-06-01", "label": "Era", "color": "#fff"}],
            },
            "title": "Test",
        }
        code = generate(instruction)
        ast.parse(code)

    def test_custom_zone_opacity(self):
        code = generate(self._make_instruction(zone_opacity=0.5))
        ast.parse(code)
        assert "0.5" in code
