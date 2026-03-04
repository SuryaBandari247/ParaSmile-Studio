"""Integration-level unit tests for pipeline_ui.

Tests:
- Panel dispatch: each PipelineStep routes to the correct render function
- Environment variable validation: all present, one missing, all missing
- Error classification: each known exception type maps to the correct category

Requirements: 1.4, 1.5, 2.1, 9.2
"""

import os
from datetime import datetime, timezone

import pytest

from pipeline_ui.app import _PANEL_DISPATCH, classify_error, validate_env_vars
from pipeline_ui.navigation import PipelineStep
from pipeline_ui.panels.convert_panel import render_convert_panel
from pipeline_ui.panels.review_panel import render_review_panel
from pipeline_ui.panels.script_input_panel import render_script_input_panel
from pipeline_ui.panels.search_panel import render_search_panel
from pipeline_ui.panels.select_topic_panel import render_select_topic_panel
from research_agent.exceptions import (
    AuthenticationError as RAAuthenticationError,
    NetworkError,
    QuotaExceededError,
)
from script_generator.exceptions import (
    AuthenticationError as SGAuthenticationError,
    ParseError as SGParseError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Panel dispatch tests (Requirement 2.1)
# ---------------------------------------------------------------------------


class TestPanelDispatch:
    """Verify _PANEL_DISPATCH maps every PipelineStep to the correct panel."""

    def test_dispatch_covers_all_steps(self):
        assert set(_PANEL_DISPATCH.keys()) == set(PipelineStep)

    def test_search_routes_to_search_panel(self):
        assert _PANEL_DISPATCH[PipelineStep.SEARCH] is render_search_panel

    def test_select_topic_routes_to_select_topic_panel(self):
        assert _PANEL_DISPATCH[PipelineStep.SELECT_TOPIC] is render_select_topic_panel

    def test_script_input_routes_to_script_input_panel(self):
        assert _PANEL_DISPATCH[PipelineStep.SCRIPT_INPUT] is render_script_input_panel

    def test_convert_routes_to_convert_panel(self):
        assert _PANEL_DISPATCH[PipelineStep.CONVERT] is render_convert_panel

    def test_review_routes_to_review_panel(self):
        assert _PANEL_DISPATCH[PipelineStep.REVIEW] is render_review_panel


# ---------------------------------------------------------------------------
# Environment variable validation tests (Requirements 1.4, 1.5)
# ---------------------------------------------------------------------------


class TestValidateEnvVars:
    """Verify validate_env_vars detects missing environment variables."""

    def test_all_present(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("YOUTUBE_API_KEY", "yt-test")
        assert validate_env_vars(["OPENAI_API_KEY", "YOUTUBE_API_KEY"]) == []

    def test_one_missing(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        result = validate_env_vars(["OPENAI_API_KEY", "YOUTUBE_API_KEY"])
        assert result == ["YOUTUBE_API_KEY"]

    def test_all_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        result = validate_env_vars(["OPENAI_API_KEY", "YOUTUBE_API_KEY"])
        assert result == ["OPENAI_API_KEY", "YOUTUBE_API_KEY"]

    def test_empty_var_list(self):
        assert validate_env_vars([]) == []


# ---------------------------------------------------------------------------
# Error classification tests (Requirement 9.2)
# ---------------------------------------------------------------------------


class TestClassifyError:
    """Verify classify_error returns the correct category for each exception."""

    # Configuration errors
    def test_research_agent_auth_error(self):
        exc = RAAuthenticationError("bad key")
        assert classify_error(exc) == "configuration"

    def test_script_generator_auth_error(self):
        exc = SGAuthenticationError("bad key")
        assert classify_error(exc) == "configuration"

    # Recoverable errors
    def test_script_generator_parse_error(self):
        exc = SGParseError("malformed json")
        assert classify_error(exc) == "recoverable"

    def test_script_generator_validation_error(self):
        exc = ValidationError("invalid input")
        assert classify_error(exc) == "recoverable"

    def test_network_error(self):
        exc = NetworkError("timeout")
        assert classify_error(exc) == "recoverable"

    def test_quota_exceeded_error(self):
        exc = QuotaExceededError(reset_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert classify_error(exc) == "recoverable"

    # Unknown errors
    def test_generic_exception_is_unknown(self):
        assert classify_error(Exception("oops")) == "unknown"

    def test_runtime_error_is_unknown(self):
        assert classify_error(RuntimeError("boom")) == "unknown"

    def test_value_error_is_unknown(self):
        assert classify_error(ValueError("bad value")) == "unknown"
