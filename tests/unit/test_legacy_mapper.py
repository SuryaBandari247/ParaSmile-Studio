"""Unit tests for LegacyMapper."""

import json
import pytest
from effects_catalog.legacy_mapper import LegacyMapper


@pytest.fixture
def mappings_file(tmp_path):
    data = {
        "data_chart": {
            "sub_type_field": "chart_type",
            "mappings": {
                "timeseries": "timeseries",
                "bar": "bar_chart",
                "donut": "donut",
            },
            "default": "timeseries",
        },
        "line_chart": {"target": "timeseries"},
        "pie_chart": {"target": "donut"},
    }
    path = tmp_path / "legacy_mappings.json"
    path.write_text(json.dumps(data))
    return path


class TestSimpleAlias:
    def test_resolves_simple_alias(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        assert mapper.resolve("line_chart") == "timeseries"
        assert mapper.resolve("pie_chart") == "donut"

    def test_unknown_type_returns_none(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        assert mapper.resolve("unknown_type") is None


class TestSubTypeDispatch:
    def test_resolves_with_sub_type(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        instruction = {"data": {"chart_type": "bar"}}
        assert mapper.resolve("data_chart", instruction) == "bar_chart"

    def test_falls_back_to_default(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        assert mapper.resolve("data_chart") == "timeseries"

    def test_unknown_sub_type_uses_default(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        instruction = {"data": {"chart_type": "unknown"}}
        assert mapper.resolve("data_chart", instruction) == "timeseries"


class TestListAliases:
    def test_returns_flat_mapping(self, mappings_file):
        mapper = LegacyMapper(mappings_file)
        aliases = mapper.list_aliases()
        assert aliases["line_chart"] == "timeseries"
        assert aliases["pie_chart"] == "donut"
        assert aliases["data_chart"] == "timeseries"  # default

    def test_empty_when_no_file(self, tmp_path):
        mapper = LegacyMapper(tmp_path / "nonexistent.json")
        assert mapper.list_aliases() == {}
