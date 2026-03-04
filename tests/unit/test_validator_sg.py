"""
Unit tests for the Validator class.

Tests per-type visual instruction validation and script-level
violation aggregation.

Requirements: 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from datetime import datetime, timezone

import pytest

from script_generator.models import SceneBlock, VideoScript
from script_generator.validator import Validator


@pytest.fixture
def validator():
    return Validator()


class TestBarChartValidation:
    """Requirements 4.2: bar_chart labels/values validation."""

    def test_valid_bar_chart_passes(self, validator):
        instruction = {
            "type": "bar_chart",
            "title": "Stats",
            "data": {"labels": ["A", "B", "C"], "values": [10, 20, 30]},
        }
        assert validator.validate_instruction(instruction) == []

    def test_mismatched_labels_values_fails(self, validator):
        instruction = {
            "type": "bar_chart",
            "title": "Stats",
            "data": {"labels": ["A", "B"], "values": [10, 20, 30]},
        }
        violations = validator.validate_instruction(instruction)
        assert len(violations) == 1
        assert "labels" in violations[0] and "values" in violations[0]


class TestPieChartValidation:
    """Requirements 4.3: pie_chart values must be positive."""

    def test_valid_pie_chart_passes(self, validator):
        instruction = {
            "type": "pie_chart",
            "title": "Distribution",
            "data": {"labels": ["X", "Y"], "values": [40, 60]},
        }
        assert validator.validate_instruction(instruction) == []

    def test_negative_values_fails(self, validator):
        instruction = {
            "type": "pie_chart",
            "title": "Distribution",
            "data": {"labels": ["X", "Y"], "values": [-5, 60]},
        }
        violations = validator.validate_instruction(instruction)
        assert any("positive" in v for v in violations)

    def test_zero_value_fails(self, validator):
        instruction = {
            "type": "pie_chart",
            "title": "Distribution",
            "data": {"labels": ["X", "Y"], "values": [0, 60]},
        }
        violations = validator.validate_instruction(instruction)
        assert any("positive" in v for v in violations)


class TestCodeSnippetValidation:
    """Requirements 4.4: code_snippet code and language validation."""

    def test_valid_code_snippet_passes(self, validator):
        instruction = {
            "type": "code_snippet",
            "title": "Example",
            "data": {"code": "print('hello')", "language": "python"},
        }
        assert validator.validate_instruction(instruction) == []

    def test_empty_code_fails(self, validator):
        instruction = {
            "type": "code_snippet",
            "title": "Example",
            "data": {"code": "", "language": "python"},
        }
        violations = validator.validate_instruction(instruction)
        assert any("code" in v for v in violations)


class TestTextOverlayValidation:
    """Requirements 4.5: text_overlay text validation."""

    def test_valid_text_overlay_passes(self, validator):
        instruction = {
            "type": "text_overlay",
            "title": "Intro",
            "data": {"text": "Welcome to the video"},
        }
        assert validator.validate_instruction(instruction) == []

    def test_empty_text_fails(self, validator):
        instruction = {
            "type": "text_overlay",
            "title": "Intro",
            "data": {"text": ""},
        }
        violations = validator.validate_instruction(instruction)
        assert any("text" in v for v in violations)


class TestUnknownType:
    """Requirements 4.6: unknown type returns violation."""

    def test_unknown_type_fails(self, validator):
        instruction = {
            "type": "video_clip",
            "title": "Clip",
            "data": {},
        }
        violations = validator.validate_instruction(instruction)
        assert len(violations) == 1
        assert "video_clip" in violations[0]


class TestValidateScript:
    """Requirements 4.1: validate_script aggregates violations across scenes."""

    def test_aggregates_violations_across_scenes(self, validator):
        script = VideoScript(
            title="Test",
            scenes=[
                SceneBlock(
                    scene_number=1,
                    narration_text="Scene one.",
                    visual_instruction={
                        "type": "bar_chart",
                        "title": "Bad Chart",
                        "data": {"labels": ["A"], "values": [1, 2]},
                    },
                ),
                SceneBlock(
                    scene_number=2,
                    narration_text="Scene two.",
                    visual_instruction={
                        "type": "text_overlay",
                        "title": "Empty",
                        "data": {"text": ""},
                    },
                ),
            ],
            generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            total_word_count=4,
        )
        violations = validator.validate_script(script)
        assert len(violations) == 2

    def test_valid_script_returns_empty(self, validator):
        script = VideoScript(
            title="Good Script",
            scenes=[
                SceneBlock(
                    scene_number=1,
                    narration_text="Hello.",
                    visual_instruction={
                        "type": "text_overlay",
                        "title": "Greeting",
                        "data": {"text": "Hello"},
                    },
                ),
            ],
            generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            total_word_count=1,
        )
        assert validator.validate_script(script) == []
