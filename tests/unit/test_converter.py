"""Unit tests for the ScriptConverter orchestrator."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from script_generator.config import ConverterConfig
from script_generator.converter import ScriptConverter, SYSTEM_PROMPT
from script_generator.exceptions import AuthenticationError, ParseError, ValidationError
from script_generator.llm_client import LLMResponse
from script_generator.models import VideoScript


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_LLM_JSON = json.dumps(
    {
        "title": "Test Video",
        "scenes": [
            {
                "scene_number": 1,
                "narration_text": "Hello world.",
                "visual_instruction": {
                    "type": "text_overlay",
                    "title": "Intro",
                    "data": {"text": "Hello"},
                },
            },
            {
                "scene_number": 2,
                "narration_text": "Here are stats.",
                "visual_instruction": {
                    "type": "bar_chart",
                    "title": "Stats",
                    "data": {"labels": ["A", "B"], "values": [10, 20]},
                },
            },
            {
                "scene_number": 3,
                "narration_text": "Some code.",
                "visual_instruction": {
                    "type": "code_snippet",
                    "title": "Code",
                    "data": {"code": "print('hi')", "language": "python"},
                },
            },
            {
                "scene_number": 4,
                "narration_text": "Distribution.",
                "visual_instruction": {
                    "type": "pie_chart",
                    "title": "Pie",
                    "data": {"labels": ["X", "Y"], "values": [60, 40]},
                },
            },
            {
                "scene_number": 5,
                "narration_text": "Goodbye.",
                "visual_instruction": {
                    "type": "text_overlay",
                    "title": "Outro",
                    "data": {"text": "Thanks for watching"},
                },
            },
        ],
        "generated_at": "2025-01-15T12:00:00+00:00",
        "total_word_count": 10,
        "metadata": {},
    }
)


def _make_llm_response(content: str = VALID_LLM_JSON) -> LLMResponse:
    return LLMResponse(
        content=content,
        prompt_tokens=150,
        completion_tokens=300,
        model="gpt-4o-mini",
    )


def _make_config(api_key: str = "sk-test-key") -> ConverterConfig:
    return ConverterConfig(openai_api_key=api_key)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestScriptConverterInit:
    """Tests for ScriptConverter initialization."""

    def test_missing_api_key_raises_authentication_error(self):
        """Req 6.5: AuthenticationError when OPENAI_API_KEY is missing."""
        config = ConverterConfig(openai_api_key="")
        with patch.dict("os.environ", {}, clear=True):
            # Force empty key by re-creating config with cleared env
            cfg = ConverterConfig.__new__(ConverterConfig)
            cfg.openai_api_key = ""
            cfg.llm_model = "gpt-4o-mini"
            cfg.log_level = "INFO"
            with pytest.raises(AuthenticationError, match="OPENAI_API_KEY"):
                ScriptConverter(config=cfg)

    @patch("script_generator.converter.LLMClient")
    def test_valid_config_creates_converter(self, mock_llm_cls):
        converter = ScriptConverter(config=_make_config())
        mock_llm_cls.assert_called_once_with(api_key="sk-test-key", model="gpt-4o-mini")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestConvertInputValidation:
    """Tests for raw_script input validation."""

    @patch("script_generator.converter.LLMClient")
    def test_empty_string_raises_validation_error(self, mock_llm_cls):
        """Req 1.2: ValidationError when raw_script is empty."""
        converter = ScriptConverter(config=_make_config())
        with pytest.raises(ValidationError, match="empty"):
            converter.convert("")

    @patch("script_generator.converter.LLMClient")
    def test_whitespace_only_raises_validation_error(self, mock_llm_cls):
        """Req 1.2: ValidationError when raw_script is whitespace-only."""
        converter = ScriptConverter(config=_make_config())
        with pytest.raises(ValidationError, match="empty"):
            converter.convert("   \n\t  ")


# ---------------------------------------------------------------------------
# Successful conversion
# ---------------------------------------------------------------------------


class TestConvertSuccess:
    """Tests for successful end-to-end conversion."""

    @patch("script_generator.converter.LLMClient")
    def test_successful_conversion_returns_video_script(self, mock_llm_cls):
        """Req 1.1, 2.5: Successful conversion with mocked LLM."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = _make_llm_response()
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())
        result = converter.convert("This is a raw script about technology.")

        assert isinstance(result, VideoScript)
        assert result.title == "Test Video"
        assert len(result.scenes) == 5
        assert result.scenes[0].narration_text == "Hello world."
        mock_llm.complete.assert_called_once()


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestConvertRetry:
    """Tests for parse/validation failure retry logic."""

    @patch("script_generator.converter.LLMClient")
    def test_parse_failure_triggers_retry(self, mock_llm_cls):
        """Req 6.1: Parse failure on first attempt triggers one retry."""
        mock_llm = MagicMock()
        # First call returns invalid JSON, second returns valid
        mock_llm.complete.side_effect = [
            _make_llm_response(content="not valid json {{{"),
            _make_llm_response(content=VALID_LLM_JSON),
        ]
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())
        result = converter.convert("A raw script.")

        assert isinstance(result, VideoScript)
        assert mock_llm.complete.call_count == 2
        # Second call should include error context
        second_call_args = mock_llm.complete.call_args_list[1]
        user_msg = second_call_args[0][1]  # positional arg: user_message
        assert "error" in user_msg.lower() or "fix" in user_msg.lower()

    @patch("script_generator.converter.LLMClient")
    def test_validation_failure_triggers_retry(self, mock_llm_cls):
        """Req 6.1: Validation failure on first attempt triggers one retry."""
        invalid_visual_json = json.dumps(
            {
                "title": "Bad Video",
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration_text": "Hello.",
                        "visual_instruction": {
                            "type": "unknown_type",
                            "title": "Bad",
                            "data": {},
                        },
                    }
                ],
                "generated_at": "2025-01-15T12:00:00+00:00",
                "total_word_count": 1,
                "metadata": {},
            }
        )
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = [
            _make_llm_response(content=invalid_visual_json),
            _make_llm_response(content=VALID_LLM_JSON),
        ]
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())
        result = converter.convert("A raw script.")

        assert isinstance(result, VideoScript)
        assert mock_llm.complete.call_count == 2

    @patch("script_generator.converter.LLMClient")
    def test_second_failure_raises_parse_error(self, mock_llm_cls):
        """Req 6.2: Second failure raises ParseError."""
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = [
            _make_llm_response(content="bad json"),
            _make_llm_response(content="still bad json"),
        ]
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())
        with pytest.raises(ParseError, match="retry"):
            converter.convert("A raw script.")

        assert mock_llm.complete.call_count == 2


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class TestConvertLogging:
    """Tests for logging behavior."""

    @patch("script_generator.converter.LLMClient")
    def test_logs_conversion_request_with_script_length(self, mock_llm_cls, caplog):
        """Req 8.1: Logs conversion request with raw script length."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = _make_llm_response()
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())
        raw = "Hello this is a test script."

        # Enable propagation so caplog captures records
        converter._logger.propagate = True
        with caplog.at_level(logging.INFO, logger="script_generator.converter"):
            converter.convert(raw)

        assert any(
            str(len(raw)) in record.message and "length" in record.message.lower()
            for record in caplog.records
        ), f"Expected log with script length {len(raw)}, got: {[r.message for r in caplog.records]}"

    @patch("script_generator.converter.LLMClient")
    def test_logs_llm_call_with_token_counts(self, mock_llm_cls, caplog):
        """Req 8.2: Logs LLM call with model, prompt tokens, completion tokens."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = _make_llm_response()
        mock_llm_cls.return_value = mock_llm

        converter = ScriptConverter(config=_make_config())

        converter._logger.propagate = True
        with caplog.at_level(logging.INFO, logger="script_generator.converter"):
            converter.convert("A test script for logging.")

        assert any(
            "prompt_tokens=150" in record.message
            and "completion_tokens=300" in record.message
            for record in caplog.records
        ), f"Expected log with token counts, got: {[r.message for r in caplog.records]}"
