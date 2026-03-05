"""Unit tests for EffectRegistry."""

import json
import pytest
from effects_catalog.catalog import EffectCatalog
from effects_catalog.legacy_mapper import LegacyMapper
from effects_catalog.registry import EffectRegistry
from effects_catalog.models import EffectCategory
from effects_catalog.exceptions import UnknownEffectError


def _write_manifest(tmp_path, entries):
    (tmp_path / "manifest.json").write_text(json.dumps(entries))


def _write_mappings(tmp_path, mappings):
    path = tmp_path / "legacy_mappings.json"
    path.write_text(json.dumps(mappings))
    return path


SAMPLE_ENTRIES = [
    {"identifier": "timeseries", "display_name": "Timeseries", "category": "data", "description": "ts"},
    {"identifier": "bar_chart", "display_name": "Bar Chart", "category": "charts", "description": "bar"},
    {"identifier": "text_overlay", "display_name": "Text Overlay", "category": "text", "description": "txt"},
]


class TestResolve:
    def test_direct_resolve(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        s = registry.resolve("timeseries")
        assert s.identifier == "timeseries"

    def test_unknown_raises(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        with pytest.raises(UnknownEffectError) as exc_info:
            registry.resolve("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_legacy_alias_resolve(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        mappings_path = _write_mappings(tmp_path, {"line_chart": {"target": "timeseries"}})
        catalog = EffectCatalog(catalog_dir=tmp_path)
        mapper = LegacyMapper(mappings_path)
        registry = EffectRegistry(catalog, legacy_mapper=mapper)
        s = registry.resolve("line_chart")
        assert s.identifier == "timeseries"

    def test_sub_type_dispatch_resolve(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        mappings_path = _write_mappings(tmp_path, {
            "data_chart": {
                "sub_type_field": "chart_type",
                "mappings": {"bar": "bar_chart"},
                "default": "timeseries",
            }
        })
        catalog = EffectCatalog(catalog_dir=tmp_path)
        mapper = LegacyMapper(mappings_path)
        registry = EffectRegistry(catalog, legacy_mapper=mapper)
        s = registry.resolve("data_chart", {"data": {"chart_type": "bar"}})
        assert s.identifier == "bar_chart"


class TestListEffects:
    def test_list_all(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        assert len(registry.list_effects()) == 3

    def test_filter_by_category(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        data_effects = registry.list_effects(category=EffectCategory.DATA)
        assert len(data_effects) == 1
        assert data_effects[0].identifier == "timeseries"

    def test_filter_empty_category(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        assert registry.list_effects(category=EffectCategory.EDITORIAL) == []


class TestListAliases:
    def test_with_mapper(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        mappings_path = _write_mappings(tmp_path, {"line_chart": {"target": "timeseries"}})
        catalog = EffectCatalog(catalog_dir=tmp_path)
        mapper = LegacyMapper(mappings_path)
        registry = EffectRegistry(catalog, legacy_mapper=mapper)
        aliases = registry.list_aliases()
        assert aliases["line_chart"] == "timeseries"

    def test_without_mapper(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        assert registry.list_aliases() == {}


class TestReload:
    def test_reload_picks_up_new_entries(self, tmp_path):
        _write_manifest(tmp_path, SAMPLE_ENTRIES[:1])
        catalog = EffectCatalog(catalog_dir=tmp_path)
        registry = EffectRegistry(catalog)
        assert len(registry.list_effects()) == 1

        _write_manifest(tmp_path, SAMPLE_ENTRIES)
        registry.reload()
        assert len(registry.list_effects()) == 3
