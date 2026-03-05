"""Unit tests for effects_catalog core data models."""

from effects_catalog.models import EffectCategory, EffectSkeleton, DEFAULT_QUALITY_PROFILES
from effects_catalog.exceptions import (
    CatalogParseError,
    ConflictError,
    EffectCatalogError,
    SchemaValidationError,
    SyncPointMismatchError,
    UnknownEffectError,
    UnknownProfileError,
)


class TestEffectCategory:
    def test_all_categories_exist(self):
        assert EffectCategory.CHARTS == "charts"
        assert EffectCategory.TEXT == "text"
        assert EffectCategory.SOCIAL == "social"
        assert EffectCategory.DATA == "data"
        assert EffectCategory.EDITORIAL == "editorial"

    def test_category_is_string(self):
        for cat in EffectCategory:
            assert isinstance(cat, str)
            assert isinstance(cat.value, str)

    def test_category_count(self):
        assert len(EffectCategory) == 7


class TestEffectSkeleton:
    def test_minimal_construction(self):
        s = EffectSkeleton(
            identifier="test",
            display_name="Test Effect",
            category=EffectCategory.DATA,
            description="A test effect",
        )
        assert s.identifier == "test"
        assert s.display_name == "Test Effect"
        assert s.category == EffectCategory.DATA
        assert s.description == "A test effect"

    def test_defaults(self):
        s = EffectSkeleton(
            identifier="x", display_name="X", category=EffectCategory.TEXT, description="x"
        )
        assert s.parameter_schema == {}
        assert s.preview_config == {}
        assert s.reference_video_path == ""
        assert s.template_module == ""
        assert s.sync_points == []
        assert s.initial_wait == 0.0
        assert "draft" in s.quality_profiles
        assert "production" in s.quality_profiles

    def test_quality_profiles_default_values(self):
        s = EffectSkeleton(
            identifier="x", display_name="X", category=EffectCategory.DATA, description="x"
        )
        assert s.quality_profiles["draft"]["resolution"] == "720p"
        assert s.quality_profiles["draft"]["fps"] == 15
        assert s.quality_profiles["production"]["resolution"] == "1080p"
        assert s.quality_profiles["production"]["fps"] == 30

    def test_custom_fields(self):
        s = EffectSkeleton(
            identifier="ts",
            display_name="Timeseries",
            category=EffectCategory.DATA,
            description="Animated timeseries",
            parameter_schema={"type": "object", "properties": {"ticker": {"type": "string"}}},
            preview_config={"ticker": "AAPL"},
            reference_video_path="assets/timeseries.mp4",
            template_module="templates.timeseries",
            sync_points=["line_start", "event_reveal"],
            initial_wait=1.5,
        )
        assert s.sync_points == ["line_start", "event_reveal"]
        assert s.initial_wait == 1.5
        assert s.template_module == "templates.timeseries"

    def test_quality_profiles_independent_per_instance(self):
        """Each skeleton gets its own copy of quality_profiles."""
        a = EffectSkeleton(identifier="a", display_name="A", category=EffectCategory.TEXT, description="a")
        b = EffectSkeleton(identifier="b", display_name="B", category=EffectCategory.TEXT, description="b")
        a.quality_profiles["custom"] = {"resolution": "4k"}
        assert "custom" not in b.quality_profiles


class TestExceptions:
    def test_unknown_effect_error(self):
        e = UnknownEffectError("foo", ["bar", "baz"])
        assert e.identifier == "foo"
        assert e.available == ["bar", "baz"]
        assert "foo" in str(e)
        assert "bar" in str(e)
        assert isinstance(e, EffectCatalogError)

    def test_conflict_error(self):
        e = ConflictError("timeseries")
        assert e.identifier == "timeseries"
        assert "timeseries" in str(e)

    def test_schema_validation_error(self):
        errors = [{"field": "ticker", "message": "required"}, {"field": "period", "message": "invalid type"}]
        e = SchemaValidationError(errors)
        assert len(e.errors) == 2
        assert "ticker" in str(e)
        assert "period" in str(e)

    def test_sync_point_mismatch_error(self):
        e = SyncPointMismatchError(3, 5)
        assert e.expected == 3
        assert e.actual == 5
        assert "3" in str(e)
        assert "5" in str(e)

    def test_unknown_profile_error(self):
        e = UnknownProfileError("ultra", ["draft", "production"])
        assert e.profile == "ultra"
        assert "ultra" in str(e)
        assert "draft" in str(e)

    def test_catalog_parse_error_with_position(self):
        e = CatalogParseError("unexpected token", position=42)
        assert e.position == 42
        assert "42" in str(e)

    def test_catalog_parse_error_without_position(self):
        e = CatalogParseError("empty file")
        assert e.position is None
        assert "empty file" in str(e)

    def test_all_inherit_from_base(self):
        for exc_cls in [UnknownEffectError, ConflictError, SchemaValidationError,
                        SyncPointMismatchError, UnknownProfileError, CatalogParseError]:
            assert issubclass(exc_cls, EffectCatalogError)
            assert issubclass(exc_cls, Exception)
