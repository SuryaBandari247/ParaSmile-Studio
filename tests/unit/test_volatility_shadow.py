"""Unit tests for the Volatility Shadow effect template."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.volatility_shadow import (
    InsufficientDataError,
    compute_drawdown_regions,
    generate,
)


class TestComputeDrawdownRegions:
    """Tests for the drawdown region computation."""

    def test_no_drawdown(self):
        """Monotonically increasing series has no drawdowns."""
        regions = compute_drawdown_regions([10, 20, 30, 40, 50])
        assert regions == []

    def test_single_drawdown(self):
        """Series with one dip should produce one region."""
        values = [100, 110, 105, 95, 100, 115]
        regions = compute_drawdown_regions(values)
        assert len(regions) == 1
        assert regions[0]["start_idx"] == 2
        assert regions[0]["end_idx"] == 4

    def test_trailing_drawdown(self):
        """Drawdown at end of series should be captured."""
        values = [100, 110, 105, 90]
        regions = compute_drawdown_regions(values)
        assert len(regions) == 1
        assert regions[0]["end_idx"] == 3

    def test_multiple_drawdowns(self):
        """Multiple separate drawdowns should produce multiple regions."""
        values = [100, 110, 95, 115, 100, 120]
        regions = compute_drawdown_regions(values)
        assert len(regions) == 2

    def test_drawdown_percentage(self):
        """Drawdown percentage should be calculated correctly."""
        values = [100, 80]  # 20% drawdown
        regions = compute_drawdown_regions(values)
        assert len(regions) == 1
        assert abs(regions[0]["max_drawdown_pct"] - 20.0) < 0.01

    def test_fewer_than_two_points(self):
        assert compute_drawdown_regions([]) == []
        assert compute_drawdown_regions([100]) == []

    def test_flat_series(self):
        """Flat series has no drawdowns."""
        regions = compute_drawdown_regions([100, 100, 100, 100])
        assert regions == []

    def test_running_max_at_start(self):
        """running_max_at_start should be the ATH when drawdown began."""
        values = [100, 120, 110, 130]
        regions = compute_drawdown_regions(values)
        assert len(regions) == 1
        assert regions[0]["running_max_at_start"] == 120


class TestGenerate:
    """Tests for Volatility Shadow Manim code generation."""

    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100, 110, 105, 95, 100, 115, 108, 120, 112, 125, 118, 130],
            "shadow_color": "#FF453A",
            "shadow_opacity": 0.2,
            "show_drawdown_pct": False,
        }
        data.update(overrides)
        return {"data": data, "title": "NVDA Drawdown"}

    def test_generates_valid_python(self):
        code = generate(self._make_instruction())
        ast.parse(code)

    def test_contains_scene_class(self):
        code = generate(self._make_instruction())
        assert "class VolatilityShadowScene(MovingCameraScene)" in code

    def test_polygon_present(self):
        code = generate(self._make_instruction())
        assert "Polygon" in code

    def test_custom_shadow_color(self):
        code = generate(self._make_instruction(shadow_color="#00FF00"))
        assert "#00FF00" in code

    def test_show_drawdown_pct(self):
        code = generate(self._make_instruction(show_drawdown_pct=True))
        assert "show_drawdown_pct" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {"dates": [], "values": []}})
        ast.parse(code)

    def test_end_of_line_badge(self):
        code = generate(self._make_instruction())
        assert "badge" in code.lower() or "last_val" in code


class TestInsufficientDataError:
    def test_error_message(self):
        err = InsufficientDataError(1)
        assert "2" in str(err)
        assert "1" in str(err)
        assert err.count == 1
