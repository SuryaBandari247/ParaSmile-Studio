"""Unit tests for the SceneExpander."""

from effects_catalog.scene_expander import SceneExpander, HIGH_IMPACT_TYPES


class TestSceneExpander:
    def setup_method(self):
        self.expander = SceneExpander()

    def test_short_data_chart_gets_padded(self):
        result = self.expander.expand_if_needed(3.0, "data_chart")
        assert result == 5.5  # 3.0 + 2.5

    def test_short_timeseries_gets_padded(self):
        result = self.expander.expand_if_needed(4.0, "timeseries")
        assert result == 6.5

    def test_long_scene_unchanged(self):
        result = self.expander.expand_if_needed(8.0, "data_chart")
        assert result == 8.0

    def test_exactly_threshold_unchanged(self):
        result = self.expander.expand_if_needed(6.0, "timeseries")
        assert result == 6.0

    def test_non_data_scene_unchanged(self):
        result = self.expander.expand_if_needed(3.0, "text_overlay")
        assert result == 3.0

    def test_custom_pad_via_overrides(self):
        result = self.expander.expand_if_needed(3.0, "data_chart", {"expansion_pad_s": 1.0})
        assert result == 4.0

    def test_all_high_impact_types_expand(self):
        for vtype in HIGH_IMPACT_TYPES:
            result = self.expander.expand_if_needed(3.0, vtype)
            assert result > 3.0, f"{vtype} should expand"

    def test_forensic_zoom_expands(self):
        result = self.expander.expand_if_needed(2.0, "forensic_zoom")
        assert result == 4.5

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("SCENE_EXPANSION_PAD_S", "5.0")
        result = self.expander.expand_if_needed(3.0, "data_chart")
        assert result == 8.0
