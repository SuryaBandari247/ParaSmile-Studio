"""Unit tests for the StaticFreezeDetector."""

from effects_catalog.static_freeze import StaticFreezeDetector


class TestExtractDelta:
    def setup_method(self):
        self.detector = StaticFreezeDetector()

    def test_delta_from_event_label(self):
        instruction = {"data": {"events": [{"label": "Dropped -16%"}]}}
        assert self.detector.extract_delta(instruction) == -16.0

    def test_delta_from_annotation(self):
        instruction = {"data": {"annotations": [{"text": "Up 25%"}]}}
        assert self.detector.extract_delta(instruction) == 25.0

    def test_delta_from_narration(self):
        instruction = {"narration": "ASML dropped 16 percent", "data": {}}
        assert self.detector.extract_delta(instruction) == 16.0

    def test_delta_from_chart_metadata(self):
        instruction = {"data": {"delta_pct": -12.5}}
        assert self.detector.extract_delta(instruction) == -12.5

    def test_no_delta_found(self):
        instruction = {"data": {"values": [100, 200]}}
        assert self.detector.extract_delta(instruction) is None


class TestDetectFreeze:
    def setup_method(self):
        self.detector = StaticFreezeDetector()

    def test_high_delta_short_narration_freezes(self):
        instruction = {"data": {"events": [{"label": "-16%"}]}}
        result = self.detector.detect_freeze(instruction, 2.5)
        assert result == 2.0

    def test_high_delta_long_narration_no_freeze(self):
        instruction = {"data": {"events": [{"label": "-16%"}]}}
        result = self.detector.detect_freeze(instruction, 4.0)
        assert result is None

    def test_low_delta_short_narration_no_freeze(self):
        instruction = {"data": {"events": [{"label": "-5%"}]}}
        result = self.detector.detect_freeze(instruction, 2.0)
        assert result is None

    def test_no_delta_no_freeze(self):
        instruction = {"data": {"values": [100]}}
        result = self.detector.detect_freeze(instruction, 1.0)
        assert result is None

    def test_custom_freeze_duration(self):
        instruction = {"data": {"events": [{"label": "-20%"}]}}
        result = self.detector.detect_freeze(instruction, 2.0, {"freeze_duration_s": 3.5})
        assert result == 3.5

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("STATIC_FREEZE_S", "4.0")
        instruction = {"data": {"events": [{"label": "-20%"}]}}
        result = self.detector.detect_freeze(instruction, 2.0)
        assert result == 4.0
