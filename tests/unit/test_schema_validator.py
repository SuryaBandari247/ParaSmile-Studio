"""Unit tests for SchemaValidator."""

import pytest
from effects_catalog.schema_validator import SchemaValidator
from effects_catalog.exceptions import SchemaValidationError


TICKER_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker": {"type": "string"},
        "period": {"type": "string", "default": "1y", "enum": ["1mo", "6mo", "1y", "2y", "5y"]},
        "events": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["ticker"],
}

NUMERIC_SCHEMA = {
    "type": "object",
    "properties": {
        "opacity": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.2},
        "count": {"type": "integer", "minimum": 1},
    },
    "required": [],
}


class TestValidParams:
    def test_valid_with_all_fields(self):
        result = SchemaValidator.validate({"ticker": "AAPL", "period": "1y"}, TICKER_SCHEMA)
        assert result["ticker"] == "AAPL"
        assert result["period"] == "1y"

    def test_defaults_applied(self):
        result = SchemaValidator.validate({"ticker": "MSFT"}, TICKER_SCHEMA)
        assert result["period"] == "1y"

    def test_numeric_defaults(self):
        result = SchemaValidator.validate({}, NUMERIC_SCHEMA)
        assert result["opacity"] == 0.2

    def test_empty_schema(self):
        result = SchemaValidator.validate({"anything": "goes"}, {})
        assert result == {"anything": "goes"}

    def test_array_items_valid(self):
        result = SchemaValidator.validate(
            {"ticker": "AAPL", "events": [{"date": "2024-01-01"}]},
            TICKER_SCHEMA,
        )
        assert len(result["events"]) == 1


class TestMissingRequired:
    def test_missing_required_field(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({}, TICKER_SCHEMA)
        assert any(e["field"] == "ticker" for e in exc_info.value.errors)

    def test_error_message_contains_field_name(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({}, TICKER_SCHEMA)
        assert "ticker" in str(exc_info.value)


class TestTypeErrors:
    def test_wrong_type_string(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"ticker": 123}, TICKER_SCHEMA)
        assert any(e["field"] == "ticker" and e["type"] == "type" for e in exc_info.value.errors)

    def test_wrong_type_number(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"opacity": "high"}, NUMERIC_SCHEMA)
        assert any(e["field"] == "opacity" for e in exc_info.value.errors)

    def test_bool_not_integer(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"count": True}, NUMERIC_SCHEMA)
        assert any(e["field"] == "count" for e in exc_info.value.errors)

    def test_bool_not_number(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"opacity": False}, NUMERIC_SCHEMA)
        assert any(e["field"] == "opacity" for e in exc_info.value.errors)


class TestEnumErrors:
    def test_invalid_enum_value(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"ticker": "AAPL", "period": "10y"}, TICKER_SCHEMA)
        assert any(e["field"] == "period" and e["type"] == "enum" for e in exc_info.value.errors)


class TestRangeErrors:
    def test_below_minimum(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"opacity": -0.5}, NUMERIC_SCHEMA)
        assert any(e["field"] == "opacity" and e["type"] == "minimum" for e in exc_info.value.errors)

    def test_above_maximum(self):
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"opacity": 1.5}, NUMERIC_SCHEMA)
        assert any(e["field"] == "opacity" and e["type"] == "maximum" for e in exc_info.value.errors)


class TestArrayItemValidation:
    def test_invalid_array_item_type(self):
        schema = {
            "type": "object",
            "properties": {
                "values": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 100}},
            },
            "required": ["values"],
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            SchemaValidator.validate({"values": [50, 200]}, schema)
        assert any("values[1]" in e["field"] for e in exc_info.value.errors)


class TestOriginalNotMutated:
    def test_defaults_dont_mutate_input(self):
        original = {"ticker": "AAPL"}
        result = SchemaValidator.validate(original, TICKER_SCHEMA)
        assert "period" not in original
        assert "period" in result
