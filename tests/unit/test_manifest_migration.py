"""Unit tests verifying all 17 existing scene types are loadable and resolvable.

Validates Requirement 2.6 (all existing scene types as pre-registered skeletons)
and Requirement 4.2 (backward compatibility through registry resolution).
"""

import pytest
from pathlib import Path

from effects_catalog.catalog import EffectCatalog
from effects_catalog.registry import EffectRegistry
from effects_catalog.legacy_mapper import LegacyMapper
from effects_catalog.models import EffectCategory


# The 17 scene types that must exist in the manifest
EXPECTED_TYPES = [
    "text_overlay",
    "bar_chart",
    "line_chart",
    "pie_chart",
    "code_snippet",
    "reddit_post",
    "stat_callout",
    "quote_block",
    "section_title",
    "bullet_reveal",
    "comparison",
    "fullscreen_statement",
    "data_chart",
    "timeseries",
    "horizontal_bar",
    "grouped_bar",
    "donut",
]

# Expected category assignments per the design doc
EXPECTED_CATEGORIES = {
    "text_overlay": EffectCategory.TEXT,
    "bar_chart": EffectCategory.CHARTS,
    "line_chart": EffectCategory.CHARTS,
    "pie_chart": EffectCategory.CHARTS,
    "code_snippet": EffectCategory.TEXT,
    "reddit_post": EffectCategory.SOCIAL,
    "stat_callout": EffectCategory.TEXT,
    "quote_block": EffectCategory.TEXT,
    "section_title": EffectCategory.TEXT,
    "bullet_reveal": EffectCategory.TEXT,
    "comparison": EffectCategory.CHARTS,
    "fullscreen_statement": EffectCategory.TEXT,
    "data_chart": EffectCategory.DATA,
    "timeseries": EffectCategory.DATA,
    "horizontal_bar": EffectCategory.CHARTS,
    "grouped_bar": EffectCategory.CHARTS,
    "donut": EffectCategory.CHARTS,
}

# Data/timeseries effects should have initial_wait=1.5
DATA_EFFECTS_WITH_WAIT = {"data_chart", "timeseries"}


@pytest.fixture()
def catalog():
    """Load the real effects_catalog/manifest.json."""
    return EffectCatalog(catalog_dir=Path("effects_catalog"))


@pytest.fixture()
def registry(catalog):
    """Build a registry with the real catalog and legacy mapper."""
    mapper = LegacyMapper(mappings_path=Path("effects_catalog/legacy_mappings.json"))
    return EffectRegistry(catalog, legacy_mapper=mapper)


class TestManifestLoadsAll17:
    def test_catalog_loads_exactly_17_skeletons(self, catalog):
        skeletons = catalog.load_all()
        assert len(skeletons) == 17

    def test_all_expected_identifiers_present(self, catalog):
        skeletons = catalog.load_all()
        loaded_ids = {s.identifier for s in skeletons}
        for expected_id in EXPECTED_TYPES:
            assert expected_id in loaded_ids, f"Missing skeleton: {expected_id}"

    def test_no_duplicate_identifiers(self, catalog):
        skeletons = catalog.load_all()
        ids = [s.identifier for s in skeletons]
        assert len(ids) == len(set(ids)), f"Duplicate identifiers found: {ids}"


class TestRegistryResolvesAll17:
    @pytest.mark.parametrize("effect_id", EXPECTED_TYPES)
    def test_resolve_by_identifier(self, registry, effect_id):
        skeleton = registry.resolve(effect_id)
        assert skeleton.identifier == effect_id

    def test_list_effects_returns_all_17(self, registry):
        all_effects = registry.list_effects()
        assert len(all_effects) == 17


class TestCategoryAssignments:
    @pytest.mark.parametrize("effect_id,expected_cat", EXPECTED_CATEGORIES.items())
    def test_category_matches_design(self, catalog, effect_id, expected_cat):
        skeleton = catalog.get_by_id(effect_id)
        assert skeleton is not None, f"Skeleton {effect_id} not found"
        assert skeleton.category == expected_cat


class TestInitialWait:
    @pytest.mark.parametrize("effect_id", DATA_EFFECTS_WITH_WAIT)
    def test_data_effects_have_initial_wait(self, catalog, effect_id):
        skeleton = catalog.get_by_id(effect_id)
        assert skeleton is not None
        assert skeleton.initial_wait == 1.5

    @pytest.mark.parametrize("effect_id", [
        eid for eid in EXPECTED_TYPES if eid not in DATA_EFFECTS_WITH_WAIT
    ])
    def test_non_data_effects_have_zero_wait(self, catalog, effect_id):
        skeleton = catalog.get_by_id(effect_id)
        assert skeleton is not None
        assert skeleton.initial_wait == 0.0


class TestSkeletonCompleteness:
    @pytest.mark.parametrize("effect_id", EXPECTED_TYPES)
    def test_has_required_fields(self, catalog, effect_id):
        skeleton = catalog.get_by_id(effect_id)
        assert skeleton is not None
        assert skeleton.identifier
        assert skeleton.display_name
        assert skeleton.description
        assert isinstance(skeleton.category, EffectCategory)
        assert isinstance(skeleton.parameter_schema, dict)
        assert isinstance(skeleton.quality_profiles, dict)
        assert "draft" in skeleton.quality_profiles
        assert "production" in skeleton.quality_profiles
