"""Unit tests for the Liquidity Shock effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.liquidity_shock import (
    DateRangeError,
    RangeError,
    generate,
)


class TestDateRangeError:
    def test_error_message(self):
        err = DateRangeError("2024-07-01", "2024-01-01", "2024-06-01")
        assert "2024-07-01" in str(err)
        assert err.shock_date == "2024-07-01"
        assert err.valid_start == "2024-01-01"
        assert err.valid_end == "2024-06-01"


class TestRangeError:
    def test_error_message(self):
        err = RangeError(1.5, "shock_intensity")
        assert "1.5" in str(err)
        assert err.value == 1.5
        assert err.field == "shock_intensity"


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100 + i * 5 - (20 if i == 6 else 0) for i in range(12)],
            "shock_date": "2024-07-01",
            "shock_color": "#FF453A",
            "shock_intensity": 0.7,
            "shock_label": "Flash Crash",
        }
        data.update(overrides)
        return {"data": data, "title": "Market Shock"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "LiquidityShockScene" in generate(self._make_instruction())

    def test_uses_moving_camera_scene(self):
        assert "MovingCameraScene" in generate(self._make_instruction())

    def test_shock_label_in_output(self):
        code = generate(self._make_instruction())
        assert "Flash Crash" in code

    def test_shock_color_in_output(self):
        code = generate(self._make_instruction())
        assert "#FF453A" in code

    def test_vertical_energy_pulse(self):
        code = generate(self._make_instruction())
        assert "streak" in code.lower() or "flash" in code.lower()

    def test_camera_shake(self):
        code = generate(self._make_instruction())
        assert "shake" in code.lower() or "camera" in code.lower()

    def test_indicate_shock_point(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code

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
                    {"date": "2024-02-01", "value": 110},
                    {"date": "2024-03-01", "value": 90},
                ]}],
                "shock_date": "2024-02-01",
            },
            "title": "Test",
        }
        code = generate(instruction)
        ast.parse(code)
        assert "LiquidityShockScene" in code

    def test_no_shock_label(self):
        code = generate(self._make_instruction(shock_label=""))
        ast.parse(code)

    def test_custom_intensity(self):
        code = generate(self._make_instruction(shock_intensity=0.3))
        ast.parse(code)
        assert "0.3" in code

    def test_flash_line(self):
        code = generate(self._make_instruction())
        assert "flash_line" in code or "Line" in code
