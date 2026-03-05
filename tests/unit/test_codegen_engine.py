"""Tests for CodegenEngine refactor — registry-driven dispatch in manim_codegen.py.

Covers: backward compat, registry dispatch, sync points, quality profiles,
style merge, initial_wait injection, and legacy fallback.
"""

from __future__ import annotations

import pytest

from asset_orchestrator.manim_codegen import generate_scene_code
from effects_catalog.catalog import EffectCatalog
from effects_catalog.exceptions import (
    SchemaValidationError,
    SyncPointMismatchError,
    UnknownEffectError,
    UnknownProfileError,
)
from effects_catalog.legacy_mapper import LegacyMapper
from effects_catalog.registry import EffectRegistry


@pytest.fixture
def registry():
    """Build a real registry from the on-disk manifest."""
    catalog = EffectCatalog("effects_catalog")
    mapper = LegacyMapper("effects_catalog/legacy_mappings.json")
    return EffectRegistry(catalog, mapper)


# ── Backward Compatibility ──────────────────────────────────────────────


class TestBackwardCompat:
    """Legacy mode: registry=None should produce the same output as before."""

    def test_text_overlay_without_registry(self):
        instruction = {"type": "text_overlay", "title": "Hello", "data": {"text": "World"}}
        code = generate_scene_code(instruction)
        assert "class TextOverlayScene(Scene):" in code
        assert "World" in code

    def test_bar_chart_without_registry(self):
        instruction = {
            "type": "bar_chart",
            "title": "Revenue",
            "data": {"labels": ["Q1", "Q2"], "values": [100, 200]},
        }
        code = generate_scene_code(instruction)
        assert "class BarChartScene(Scene):" in code

    def test_unknown_type_falls_back_to_text_overlay(self):
        instruction = {"type": "nonexistent_type", "data": {"text": "fallback"}}
        code = generate_scene_code(instruction)
        assert "class TextOverlayScene(Scene):" in code

    def test_data_chart_routes_to_bar(self):
        instruction = {
            "type": "data_chart",
            "data": {"chart_type": "bar", "labels": ["A"], "values": [10]},
        }
        code = generate_scene_code(instruction)
        assert "BarChartScene" in code

    def test_timeseries_without_registry(self):
        instruction = {
            "type": "timeseries",
            "title": "Stock",
            "data": {
                "dates": ["2024-01", "2024-02", "2024-03"],
                "series": [{"name": "AAPL", "values": [150, 160, 155]}],
            },
        }
        code = generate_scene_code(instruction)
        assert "class TimeseriesScene(MovingCameraScene):" in code


# ── Registry-Driven Dispatch ────────────────────────────────────────────


class TestRegistryDispatch:
    """Registry path: resolve → validate → generate."""

    def test_text_overlay_with_registry(self, registry):
        instruction = {"type": "text_overlay", "title": "Hello", "data": {"text": "World"}}
        code = generate_scene_code(instruction, registry=registry)
        assert "class TextOverlayScene(Scene):" in code
        assert "World" in code

    def test_bar_chart_with_registry(self, registry):
        instruction = {
            "type": "bar_chart",
            "title": "Revenue",
            "data": {"labels": ["Q1", "Q2"], "values": [100, 200]},
        }
        code = generate_scene_code(instruction, registry=registry)
        assert "BarChartScene" in code

    def test_unknown_effect_raises(self, registry):
        instruction = {"type": "totally_unknown_effect", "data": {}}
        with pytest.raises(UnknownEffectError):
            generate_scene_code(instruction, registry=registry)

    def test_legacy_alias_data_chart_resolves(self, registry):
        """data_chart with chart_type=timeseries should resolve via LegacyMapper."""
        instruction = {
            "type": "data_chart",
            "data": {
                "chart_type": "timeseries",
                "dates": ["2024-01", "2024-02"],
                "series": [{"name": "X", "values": [10, 20]}],
            },
        }
        code = generate_scene_code(instruction, registry=registry)
        assert "TimeseriesScene" in code

    def test_all_17_types_resolve(self, registry):
        """Every manifest type should resolve without error."""
        # Provide minimal valid data for types with required fields
        type_data = {
            "text_overlay": {"text": "test"},
            "bar_chart": {"labels": ["A"], "values": [1]},
            "line_chart": {"labels": ["A"], "values": [1]},
            "pie_chart": {"labels": ["A"], "values": [1]},
            "code_snippet": {"code": "x = 1"},
            "reddit_post": {"subreddit": "r/test", "post_title": "Test"},
            "stat_callout": {"value": "42", "label": "Test"},
            "quote_block": {"quote": "Test quote"},
            "section_title": {"heading": "Test"},
            "bullet_reveal": {"bullets": ["item"]},
            "comparison": {"left_title": "A", "right_title": "B", "left_items": ["x"], "right_items": ["y"]},
            "fullscreen_statement": {"statement": "Test"},
            "data_chart": {},
            "timeseries": {},
            "horizontal_bar": {"labels": ["A"], "values": [1]},
            "grouped_bar": {"labels": ["A"], "series": [{"name": "S", "values": [1]}]},
            "donut": {"labels": ["A"], "values": [1]},
        }
        for t, data in type_data.items():
            instruction = {"type": t, "data": data}
            code = generate_scene_code(instruction, registry=registry)
            assert "class " in code, f"Failed for type: {t}"


# ── Quality Profiles ────────────────────────────────────────────────────


class TestQualityProfiles:
    def test_production_profile_accepted(self, registry):
        instruction = {"type": "text_overlay", "data": {"text": "test"}}
        code = generate_scene_code(instruction, registry=registry, quality_profile="production")
        assert "TextOverlayScene" in code

    def test_draft_profile_accepted(self, registry):
        instruction = {"type": "text_overlay", "data": {"text": "test"}}
        code = generate_scene_code(instruction, registry=registry, quality_profile="draft")
        assert "TextOverlayScene" in code

    def test_unknown_profile_raises(self, registry):
        instruction = {"type": "text_overlay", "data": {"text": "test"}}
        with pytest.raises(UnknownProfileError):
            generate_scene_code(instruction, registry=registry, quality_profile="ultra_hd")


# ── Sync Points ─────────────────────────────────────────────────────────


class TestSyncPoints:
    def test_sync_waits_injected_for_timeseries(self, registry):
        """Timeseries has sync_points — providing matching timestamps should work."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02", "2024-03"],
                "series": [{"name": "AAPL", "values": [150, 160, 155]}],
            },
        }
        # timeseries has 3 sync_points: line_start, event_marker_reveal, end_badge
        timestamps = [0.5, 2.0, 4.5]
        code = generate_scene_code(instruction, registry=registry, audio_timestamps=timestamps)
        assert "sync_point: line_start @ 0.50s" in code
        assert "sync_point: event_marker_reveal @ 2.00s" in code
        assert "sync_point: end_badge @ 4.50s" in code

    def test_sync_point_mismatch_raises(self, registry):
        """Wrong number of timestamps should raise SyncPointMismatchError."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02"],
                "series": [{"name": "X", "values": [10, 20]}],
            },
        }
        # timeseries has 3 sync_points but we provide 2
        with pytest.raises(SyncPointMismatchError):
            generate_scene_code(instruction, registry=registry, audio_timestamps=[1.0, 2.0])

    def test_no_sync_points_no_timestamps_ok(self, registry):
        """Effects without sync_points should work fine without timestamps."""
        instruction = {"type": "text_overlay", "data": {"text": "no sync"}}
        code = generate_scene_code(instruction, registry=registry, audio_timestamps=None)
        assert "sync_point" not in code

    def test_sync_points_ignored_when_no_timestamps(self, registry):
        """Timeseries has sync_points but no timestamps provided — should still work."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02"],
                "series": [{"name": "X", "values": [10, 20]}],
            },
        }
        code = generate_scene_code(instruction, registry=registry, audio_timestamps=None)
        assert "sync_point" not in code


# ── Initial Wait ────────────────────────────────────────────────────────


class TestInitialWait:
    def test_data_effect_gets_initial_wait(self, registry):
        """data_chart and timeseries have initial_wait=1.5 in manifest."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02", "2024-03"],
                "series": [{"name": "X", "values": [10, 20, 15]}],
            },
        }
        code = generate_scene_code(instruction, registry=registry)
        assert "self.wait(1.5)  # initial_wait" in code

    def test_text_effect_no_initial_wait(self, registry):
        """text_overlay has initial_wait=0 — no wait injected."""
        instruction = {"type": "text_overlay", "data": {"text": "hello"}}
        code = generate_scene_code(instruction, registry=registry)
        assert "initial_wait" not in code

    def test_style_override_initial_wait(self, registry):
        """style_overrides can override the skeleton's initial_wait."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02", "2024-03"],
                "series": [{"name": "X", "values": [10, 20, 15]}],
            },
            "style_overrides": {"initial_wait": 3.0},
        }
        code = generate_scene_code(instruction, registry=registry)
        assert "self.wait(3.0)  # initial_wait" in code

    def test_style_override_zero_disables_wait(self, registry):
        """Setting initial_wait=0 via style_overrides should disable it."""
        instruction = {
            "type": "timeseries",
            "data": {
                "dates": ["2024-01", "2024-02", "2024-03"],
                "series": [{"name": "X", "values": [10, 20, 15]}],
            },
            "style_overrides": {"initial_wait": 0},
        }
        code = generate_scene_code(instruction, registry=registry)
        assert "initial_wait" not in code
