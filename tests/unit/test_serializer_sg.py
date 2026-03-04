"""
Unit tests for ScriptSerializer.

Tests round-trip serialization, ParseError on missing/invalid fields,
malformed JSON, and ISO 8601 timestamp formatting.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import json
from datetime import datetime, timezone

import pytest

from script_generator.exceptions import ParseError
from script_generator.models import SceneBlock, VideoScript
from script_generator.serializer import ScriptSerializer


@pytest.fixture
def serializer():
    return ScriptSerializer()


@pytest.fixture
def sample_script():
    """A known VideoScript for round-trip testing."""
    return VideoScript(
        title="Test Video",
        scenes=[
            SceneBlock(
                scene_number=1,
                narration_text="Welcome to the video.",
                visual_instruction={
                    "type": "text_overlay",
                    "title": "Intro",
                    "data": {"text": "Welcome"},
                },
            ),
            SceneBlock(
                scene_number=2,
                narration_text="Here are the stats.",
                visual_instruction={
                    "type": "bar_chart",
                    "title": "Stats",
                    "data": {"labels": ["A", "B"], "values": [10, 20]},
                },
            ),
        ],
        generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        total_word_count=9,
        metadata={"source": "gemini"},
    )


class TestRoundTrip:
    """Requirement 5.3: serialize then deserialize produces equivalent object."""

    def test_round_trip_preserves_all_fields(self, serializer, sample_script):
        json_str = serializer.serialize(sample_script)
        restored = serializer.deserialize(json_str)

        assert restored.title == sample_script.title
        assert len(restored.scenes) == len(sample_script.scenes)
        assert restored.total_word_count == sample_script.total_word_count
        assert restored.metadata == sample_script.metadata
        assert restored.generated_at == sample_script.generated_at

        for orig, rest in zip(sample_script.scenes, restored.scenes):
            assert rest.scene_number == orig.scene_number
            assert rest.narration_text == orig.narration_text
            assert rest.visual_instruction == orig.visual_instruction


class TestParseErrorMissingFields:
    """Requirement 5.4: ParseError on missing required fields."""

    def test_missing_title_raises_parse_error(self, serializer):
        data = json.dumps({
            "scenes": [],
            "generated_at": "2025-01-15T12:00:00+00:00",
        })
        with pytest.raises(ParseError, match="Missing required field: title"):
            serializer.deserialize(data)

    def test_missing_scenes_raises_parse_error(self, serializer):
        data = json.dumps({
            "title": "Test",
            "generated_at": "2025-01-15T12:00:00+00:00",
        })
        with pytest.raises(ParseError, match="Missing required field: scenes"):
            serializer.deserialize(data)


class TestParseErrorMalformedJSON:
    """Requirement 5.4: ParseError on malformed JSON string."""

    def test_malformed_json_raises_parse_error(self, serializer):
        with pytest.raises(ParseError, match="Malformed JSON"):
            serializer.deserialize("not valid json {{{")

    def test_empty_string_raises_parse_error(self, serializer):
        with pytest.raises(ParseError, match="Malformed JSON"):
            serializer.deserialize("")


class TestISO8601Timestamp:
    """Requirement 5.5: Timestamps formatted in ISO 8601."""

    def test_generated_at_is_iso8601(self, serializer, sample_script):
        json_str = serializer.serialize(sample_script)
        data = json.loads(json_str)
        ts = data["generated_at"]
        # Should parse back without error — valid ISO 8601
        parsed = datetime.fromisoformat(ts)
        assert parsed == sample_script.generated_at
        # ISO 8601 contains 'T' separator
        assert "T" in ts
