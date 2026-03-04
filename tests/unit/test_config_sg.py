"""
Unit tests for Script Converter models and configuration.

Tests ConverterConfig defaults, env var loading, and validation.
Requirements: 7.1, 7.2, 7.3, 7.4
"""

import os
import pytest

from script_generator.config import ConverterConfig
from script_generator.exceptions import ValidationError
from script_generator.models import SceneBlock, VideoScript
from datetime import datetime, timezone


class TestConverterConfigDefaults:
    """Test that ConverterConfig applies correct defaults."""

    def test_default_llm_model(self):
        """Default llm_model should be gpt-4o-mini."""
        config = ConverterConfig(openai_api_key="test-key")
        assert config.llm_model == "gpt-4o-mini"

    def test_default_log_level(self):
        """Default log_level should be INFO."""
        config = ConverterConfig(openai_api_key="test-key")
        assert config.log_level == "INFO"


class TestConverterConfigEnvVar:
    """Test OPENAI_API_KEY loading from environment."""

    def test_api_key_loaded_from_env(self, monkeypatch):
        """OPENAI_API_KEY env var should populate openai_api_key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test-key")
        config = ConverterConfig()
        assert config.openai_api_key == "sk-env-test-key"

    def test_explicit_key_takes_precedence(self, monkeypatch):
        """Explicitly passed key should override env var."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        config = ConverterConfig(openai_api_key="sk-explicit-key")
        assert config.openai_api_key == "sk-explicit-key"


class TestConverterConfigValidation:
    """Test that invalid config values raise ValidationError."""

    def test_invalid_log_level_raises(self):
        """Invalid log_level should raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid log_level"):
            ConverterConfig(openai_api_key="key", log_level="VERBOSE")

    def test_empty_llm_model_raises(self):
        """Empty llm_model should raise ValidationError."""
        with pytest.raises(ValidationError, match="llm_model must not be empty"):
            ConverterConfig(openai_api_key="key", llm_model="")

    def test_whitespace_llm_model_raises(self):
        """Whitespace-only llm_model should raise ValidationError."""
        with pytest.raises(ValidationError, match="llm_model must not be empty"):
            ConverterConfig(openai_api_key="key", llm_model="   ")

    def test_log_level_normalized_to_upper(self):
        """log_level should be normalized to uppercase."""
        config = ConverterConfig(openai_api_key="key", log_level="debug")
        assert config.log_level == "DEBUG"


class TestSceneBlock:
    """Basic smoke tests for SceneBlock dataclass."""

    def test_scene_block_creation(self):
        block = SceneBlock(
            scene_number=1,
            narration_text="Hello world",
            visual_instruction={"type": "text_overlay", "title": "Intro", "data": {"text": "Hello"}},
        )
        assert block.scene_number == 1
        assert block.narration_text == "Hello world"
        assert block.visual_instruction["type"] == "text_overlay"


class TestVideoScript:
    """Basic smoke tests for VideoScript dataclass."""

    def test_video_script_creation(self):
        scene = SceneBlock(
            scene_number=1,
            narration_text="Test narration",
            visual_instruction={"type": "text_overlay", "title": "T", "data": {"text": "Hi"}},
        )
        now = datetime.now(timezone.utc)
        script = VideoScript(
            title="Test Video",
            scenes=[scene],
            generated_at=now,
            total_word_count=2,
        )
        assert script.title == "Test Video"
        assert len(script.scenes) == 1
        assert script.generated_at == now
        assert script.total_word_count == 2
        assert script.metadata == {}

    def test_video_script_metadata_default(self):
        """metadata should default to empty dict."""
        script = VideoScript(
            title="T",
            scenes=[],
            generated_at=datetime.now(timezone.utc),
            total_word_count=0,
        )
        assert script.metadata == {}
