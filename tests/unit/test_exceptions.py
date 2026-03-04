"""Unit tests for the asset orchestrator exception hierarchy."""

import pytest

from asset_orchestrator.exceptions import (
    AssetOrchestratorError,
    CompositionError,
    DuplicateSceneTypeError,
    ParseError,
    RenderError,
    UnknownSceneTypeError,
    ValidationError,
)


class TestAssetOrchestratorError:
    def test_is_base_exception(self):
        err = AssetOrchestratorError("test")
        assert isinstance(err, Exception)

    def test_message(self):
        err = AssetOrchestratorError("something went wrong")
        assert str(err) == "something went wrong"


class TestValidationError:
    def test_inherits_base(self):
        err = ValidationError(["type"])
        assert isinstance(err, AssetOrchestratorError)

    def test_missing_fields_stored(self):
        fields = ["type", "title"]
        err = ValidationError(fields)
        assert err.missing_fields == fields

    def test_message_lists_fields(self):
        err = ValidationError(["type", "title", "data"])
        assert str(err) == "Missing required fields: type, title, data"

    def test_single_field(self):
        err = ValidationError(["data"])
        assert str(err) == "Missing required fields: data"


class TestUnknownSceneTypeError:
    def test_inherits_base(self):
        err = UnknownSceneTypeError("foo", ["bar_chart"])
        assert isinstance(err, AssetOrchestratorError)

    def test_attributes_stored(self):
        err = UnknownSceneTypeError("foo", ["bar_chart", "line_chart"])
        assert err.invalid_type == "foo"
        assert err.valid_types == ["bar_chart", "line_chart"]

    def test_message(self):
        err = UnknownSceneTypeError("unknown", ["bar_chart", "pie_chart"])
        assert "Unknown scene type 'unknown'" in str(err)
        assert "Valid types: bar_chart, pie_chart" in str(err)


class TestDuplicateSceneTypeError:
    def test_inherits_base(self):
        err = DuplicateSceneTypeError("bar_chart")
        assert isinstance(err, AssetOrchestratorError)

    def test_type_key_stored(self):
        err = DuplicateSceneTypeError("bar_chart")
        assert err.type_key == "bar_chart"

    def test_message(self):
        err = DuplicateSceneTypeError("bar_chart")
        assert str(err) == "Scene type 'bar_chart' is already registered"


class TestRenderError:
    def test_inherits_base(self):
        err = RenderError("segfault", {"type": "bar_chart"})
        assert isinstance(err, AssetOrchestratorError)

    def test_attributes_stored(self):
        instruction = {"type": "bar_chart", "title": "Test"}
        err = RenderError("manim crashed", instruction)
        assert err.error_output == "manim crashed"
        assert err.instruction is instruction

    def test_message(self):
        err = RenderError("exit code 1", {"type": "bar_chart"})
        assert str(err) == "Render failed: exit code 1"


class TestCompositionError:
    def test_inherits_base(self):
        err = CompositionError("codec error", "ffmpeg -i a.mp4")
        assert isinstance(err, AssetOrchestratorError)

    def test_attributes_stored(self):
        err = CompositionError("codec error", "ffmpeg -i a.mp4")
        assert err.error_output == "codec error"
        assert err.command == "ffmpeg -i a.mp4"

    def test_message(self):
        err = CompositionError("codec error", "ffmpeg -i a.mp4")
        assert str(err) == "FFmpeg composition failed: codec error"


class TestParseError:
    def test_inherits_base(self):
        err = ParseError(5, "unexpected token")
        assert isinstance(err, AssetOrchestratorError)

    def test_position_stored(self):
        err = ParseError(42, "unexpected token")
        assert err.position == 42

    def test_message_includes_position(self):
        err = ParseError(10, "unexpected comma")
        assert str(err) == "JSON parse error at position 10: unexpected comma"
