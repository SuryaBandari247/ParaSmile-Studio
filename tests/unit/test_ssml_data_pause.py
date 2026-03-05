"""Unit tests for the SSMLDataPauseInjector."""

from effects_catalog.ssml_data_pause import SSMLDataPauseInjector


class TestInjectPauses:
    def setup_method(self):
        self.injector = SSMLDataPauseInjector()

    def test_high_pct_gets_break(self):
        result = self.injector.inject_pauses("dropped 16 percent today")
        assert '<break time="1000ms"/>' in result
        assert "16 percent" in result

    def test_low_pct_no_break(self):
        result = self.injector.inject_pauses("grew 3 percent this quarter")
        assert "<break" not in result

    def test_exactly_10_pct_gets_break(self):
        result = self.injector.inject_pauses("fell 10%")
        assert "<break" in result

    def test_currency_billion_gets_break(self):
        result = self.injector.inject_pauses("revenue hit $22 billion")
        assert "<break" in result

    def test_currency_small_no_break(self):
        result = self.injector.inject_pauses("costs were $0.5 billion")
        assert "<break" not in result

    def test_trillion_gets_break(self):
        result = self.injector.inject_pauses("market cap reached $2 trillion")
        assert "<break" in result

    def test_long_scene_skips_injection(self):
        result = self.injector.inject_pauses("dropped 50 percent", scene_duration_s=9.0)
        assert "<break" not in result

    def test_exactly_8s_skips(self):
        result = self.injector.inject_pauses("dropped 50 percent", scene_duration_s=8.0)
        assert "<break" not in result

    def test_under_8s_injects(self):
        result = self.injector.inject_pauses("dropped 50 percent", scene_duration_s=7.9)
        assert "<break" in result

    def test_custom_pause_ms(self):
        result = self.injector.inject_pauses("dropped 20%", data_pause_ms=500)
        assert '<break time="500ms"/>' in result

    def test_no_data_phrases_unchanged(self):
        text = "The company reported strong earnings"
        result = self.injector.inject_pauses(text)
        assert result == text

    def test_multiple_phrases(self):
        text = "dropped 16 percent and revenue hit $5 billion"
        result = self.injector.inject_pauses(text)
        assert result.count("<break") == 2

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DATA_PAUSE_MS", "2000")
        result = self.injector.inject_pauses("dropped 20%")
        assert '<break time="2000ms"/>' in result
