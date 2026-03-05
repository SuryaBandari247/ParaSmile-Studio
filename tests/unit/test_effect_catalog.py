"""Unit tests for EffectCatalog persistence layer."""

import json
import pytest
from pathlib import Path

from effects_catalog.catalog import EffectCatalog
from effects_catalog.models import EffectCategory, EffectSkeleton
from effects_catalog.exceptions import CatalogParseError, ConflictError


def _make_skeleton(**overrides) -> EffectSkeleton:
    defaults = dict(
        identifier="test_effect",
        display_name="Test Effect",
        category=EffectCategory.DATA,
        description="A test effect",
    )
    defaults.update(overrides)
    return EffectSkeleton(**defaults)


class TestLoadAll:
    def test_empty_manifest(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("[]")
        catalog = EffectCatalog(catalog_dir=tmp_path)
        assert catalog.load_all() == []

    def test_missing_manifest_returns_empty(self, tmp_path):
        catalog = EffectCatalog(catalog_dir=tmp_path)
        assert catalog.load_all() == []

    def test_loads_valid_entry(self, tmp_path):
        entry = {
            "identifier": "ts",
            "display_name": "Timeseries",
            "category": "data",
            "description": "Animated timeseries",
        }
        (tmp_path / "manifest.json").write_text(json.dumps([entry]))
        catalog = EffectCatalog(catalog_dir=tmp_path)
        skeletons = catalog.load_all()
        assert len(skeletons) == 1
        assert skeletons[0].identifier == "ts"
        assert skeletons[0].category == EffectCategory.DATA

    def test_malformed_json_raises_parse_error(self, tmp_path):
        (tmp_path / "manifest.json").write_text("{not valid json")
        catalog = EffectCatalog(catalog_dir=tmp_path)
        with pytest.raises(CatalogParseError):
            catalog.load_all()

    def test_non_array_root_raises_parse_error(self, tmp_path):
        (tmp_path / "manifest.json").write_text('{"not": "an array"}')
        catalog = EffectCatalog(catalog_dir=tmp_path)
        with pytest.raises(CatalogParseError):
            catalog.load_all()

    def test_malformed_entry_skipped(self, tmp_path):
        entries = [
            {"identifier": "good", "display_name": "Good", "category": "text", "description": "ok"},
            {"bad": "entry"},  # missing required fields
        ]
        (tmp_path / "manifest.json").write_text(json.dumps(entries))
        catalog = EffectCatalog(catalog_dir=tmp_path)
        skeletons = catalog.load_all()
        assert len(skeletons) == 1
        assert skeletons[0].identifier == "good"

    def test_missing_template_warns_but_loads(self, tmp_path):
        entry = {
            "identifier": "ts",
            "display_name": "Timeseries",
            "category": "data",
            "description": "desc",
            "template_module": "templates.timeseries",
        }
        (tmp_path / "manifest.json").write_text(json.dumps([entry]))
        (tmp_path / "templates").mkdir()
        # No timeseries.py file — should warn but still load
        catalog = EffectCatalog(catalog_dir=tmp_path)
        skeletons = catalog.load_all()
        assert len(skeletons) == 1

    def test_missing_reference_video_warns_but_loads(self, tmp_path):
        entry = {
            "identifier": "ts",
            "display_name": "Timeseries",
            "category": "data",
            "description": "desc",
            "reference_video_path": "assets/timeseries.mp4",
        }
        (tmp_path / "manifest.json").write_text(json.dumps([entry]))
        catalog = EffectCatalog(catalog_dir=tmp_path)
        skeletons = catalog.load_all()
        assert len(skeletons) == 1


class TestGetById:
    def test_found(self, tmp_path):
        entries = [
            {"identifier": "a", "display_name": "A", "category": "text", "description": "a"},
            {"identifier": "b", "display_name": "B", "category": "data", "description": "b"},
        ]
        (tmp_path / "manifest.json").write_text(json.dumps(entries))
        catalog = EffectCatalog(catalog_dir=tmp_path)
        result = catalog.get_by_id("b")
        assert result is not None
        assert result.identifier == "b"

    def test_not_found(self, tmp_path):
        (tmp_path / "manifest.json").write_text("[]")
        catalog = EffectCatalog(catalog_dir=tmp_path)
        assert catalog.get_by_id("nonexistent") is None


class TestSave:
    def test_save_new_skeleton(self, tmp_path):
        (tmp_path / "manifest.json").write_text("[]")
        catalog = EffectCatalog(catalog_dir=tmp_path)
        skeleton = _make_skeleton()
        catalog.save(skeleton)

        loaded = catalog.load_all()
        assert len(loaded) == 1
        assert loaded[0].identifier == "test_effect"

    def test_save_conflict_raises(self, tmp_path):
        (tmp_path / "manifest.json").write_text("[]")
        catalog = EffectCatalog(catalog_dir=tmp_path)
        catalog.save(_make_skeleton())
        with pytest.raises(ConflictError):
            catalog.save(_make_skeleton())

    def test_save_creates_manifest_dir(self, tmp_path):
        nested = tmp_path / "deep" / "catalog"
        catalog = EffectCatalog(catalog_dir=nested)
        catalog.save(_make_skeleton())
        assert (nested / "manifest.json").exists()


class TestSerializeDeserialize:
    def test_round_trip(self):
        original = _make_skeleton(
            sync_points=["start", "end"],
            initial_wait=1.5,
            quality_profiles={"draft": {"resolution": "720p"}},
        )
        data = EffectCatalog.serialize(original)
        restored = EffectCatalog.deserialize(data)
        assert restored.identifier == original.identifier
        assert restored.display_name == original.display_name
        assert restored.category == original.category
        assert restored.description == original.description
        assert restored.sync_points == original.sync_points
        assert restored.initial_wait == original.initial_wait
        assert restored.quality_profiles == original.quality_profiles

    def test_serialize_produces_json_compatible(self):
        skeleton = _make_skeleton()
        data = EffectCatalog.serialize(skeleton)
        # Should be JSON-serializable
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_deserialize_applies_defaults(self):
        minimal = {
            "identifier": "x",
            "display_name": "X",
            "category": "text",
            "description": "x",
        }
        skeleton = EffectCatalog.deserialize(minimal)
        assert skeleton.parameter_schema == {}
        assert skeleton.sync_points == []
        assert skeleton.initial_wait == 0.0
        assert "draft" in skeleton.quality_profiles
        assert "production" in skeleton.quality_profiles
