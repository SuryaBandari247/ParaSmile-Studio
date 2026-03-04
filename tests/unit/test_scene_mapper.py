"""Unit tests for asset_orchestrator.scene_mapper.SceneMapper."""

import json

import pytest

from asset_orchestrator.exceptions import ParseError, UnknownSceneTypeError, ValidationError
from asset_orchestrator.scene_mapper import SceneMapper
from asset_orchestrator.scene_registry import SceneRegistry


@pytest.fixture
def registry():
    return SceneRegistry()


@pytest.fixture
def mapper(registry):
    return SceneMapper(registry)


# --- map() happy path ---

def test_map_returns_scene_with_correct_attributes(mapper):
    instruction = {"type": "bar_chart", "title": "Revenue", "data": {"labels": ["A"], "values": [1]}}
    scene = mapper.map(instruction)
    assert scene.title == "Revenue"
    assert scene.data == {"labels": ["A"], "values": [1]}
    assert scene.style is None


def test_map_passes_style_to_scene(mapper):
    instruction = {
        "type": "line_chart",
        "title": "Trend",
        "data": {"labels": ["X"], "values": [5]},
        "style": {"color": "red"},
    }
    scene = mapper.map(instruction)
    assert scene.style == {"color": "red"}


# --- map() validation errors ---

def test_map_raises_validation_error_missing_type(mapper):
    with pytest.raises(ValidationError) as exc_info:
        mapper.map({"title": "T", "data": {}})
    assert "type" in exc_info.value.missing_fields


def test_map_raises_validation_error_missing_title(mapper):
    with pytest.raises(ValidationError) as exc_info:
        mapper.map({"type": "bar_chart", "data": {}})
    assert "title" in exc_info.value.missing_fields


def test_map_raises_validation_error_missing_data(mapper):
    with pytest.raises(ValidationError) as exc_info:
        mapper.map({"type": "bar_chart", "title": "T"})
    assert "data" in exc_info.value.missing_fields


def test_map_raises_validation_error_multiple_missing(mapper):
    with pytest.raises(ValidationError) as exc_info:
        mapper.map({})
    assert set(exc_info.value.missing_fields) == {"type", "title", "data"}


# --- map() unknown type ---

def test_map_raises_unknown_scene_type_error(mapper):
    with pytest.raises(UnknownSceneTypeError) as exc_info:
        mapper.map({"type": "unknown_type", "title": "T", "data": {}})
    assert exc_info.value.invalid_type == "unknown_type"
    assert "bar_chart" in exc_info.value.valid_types


# --- serialize ---

def test_serialize_produces_valid_json(mapper):
    instruction = {"type": "pie_chart", "title": "Share", "data": {"labels": ["A"], "values": [100]}}
    result = mapper.serialize(instruction)
    assert json.loads(result) == instruction


# --- deserialize ---

def test_deserialize_returns_dict(mapper):
    raw = '{"type": "bar_chart", "title": "T", "data": {}}'
    assert mapper.deserialize(raw) == {"type": "bar_chart", "title": "T", "data": {}}


def test_deserialize_raises_parse_error_on_invalid_json(mapper):
    with pytest.raises(ParseError) as exc_info:
        mapper.deserialize("{bad json}")
    assert exc_info.value.position is not None


def test_deserialize_parse_error_contains_position(mapper):
    with pytest.raises(ParseError) as exc_info:
        mapper.deserialize('{"key": }')
    assert exc_info.value.position > 0
