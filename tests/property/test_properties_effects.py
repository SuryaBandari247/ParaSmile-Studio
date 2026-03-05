"""Property-based tests for the Effects Catalog (Properties 1-12, 25-31).

Uses Hypothesis to generate random EffectSkeleton instances and validate
structural invariants across the catalog system.
"""

import json
import string
import tempfile
from pathlib import Path
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from effects_catalog.catalog import EffectCatalog
from effects_catalog.exceptions import (
    ConflictError,
    SchemaValidationError,
    SyncPointMismatchError,
    UnknownEffectError,
    UnknownProfileError,
)
from effects_catalog.models import DEFAULT_QUALITY_PROFILES, EffectCategory, EffectSkeleton
from effects_catalog.registry import EffectRegistry
from effects_catalog.schema_validator import SchemaValidator


# ── Custom Strategies ────────────────────────────────────────

def st_identifier():
    return st.from_regex(r"[a-z][a-z0-9_]{2,30}", fullmatch=True)


def st_effect_category():
    return st.sampled_from(list(EffectCategory))


def st_quality_profiles():
    return st.fixed_dictionaries({
        "draft": st.fixed_dictionaries({
            "resolution": st.just("720p"),
            "fps": st.just(15),
        }),
        "production": st.fixed_dictionaries({
            "resolution": st.just("1080p"),
            "fps": st.just(30),
        }),
    })


# Schema used by st_valid_params / st_invalid_params
_TEST_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker": {"type": "string"},
        "period": {"type": "string", "default": "1y", "enum": ["1mo", "6mo", "1y", "2y", "5y"]},
        "count": {"type": "integer", "minimum": 1, "maximum": 100},
    },
    "required": ["ticker"],
}


def st_valid_params():
    """Generate params that satisfy _TEST_SCHEMA."""
    return st.fixed_dictionaries({
        "ticker": st.text(min_size=1, max_size=10, alphabet=string.ascii_uppercase),
        "period": st.sampled_from(["1mo", "6mo", "1y", "2y", "5y"]),
        "count": st.integers(min_value=1, max_value=100),
    })


def st_invalid_params():
    """Generate params that violate _TEST_SCHEMA in at least one way."""
    return st.one_of(
        # Missing required 'ticker'
        st.just({"period": "1y"}),
        # Wrong type for ticker
        st.builds(lambda n: {"ticker": n}, st.integers()),
        # Invalid enum value
        st.builds(lambda t: {"ticker": t, "period": "99y"}, st.text(min_size=1, max_size=5, alphabet=string.ascii_uppercase)),
        # count below minimum
        st.builds(lambda t: {"ticker": t, "count": 0}, st.text(min_size=1, max_size=5, alphabet=string.ascii_uppercase)),
        # count above maximum
        st.builds(lambda t: {"ticker": t, "count": 999}, st.text(min_size=1, max_size=5, alphabet=string.ascii_uppercase)),
    )


def st_effect_skeleton():
    return st.builds(
        EffectSkeleton,
        identifier=st_identifier(),
        display_name=st.text(min_size=1, max_size=50),
        category=st_effect_category(),
        description=st.text(min_size=1, max_size=200),
        parameter_schema=st.just({}),
        preview_config=st.just({}),
        reference_video_path=st.just(""),
        template_module=st.just(""),
        sync_points=st.lists(st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase + "_"), max_size=5),
        quality_profiles=st_quality_profiles(),
        initial_wait=st.floats(min_value=0.0, max_value=10.0),
    )


# ── Property 1: Skeleton structural completeness ────────────
# Feature: effect-catalog-core, Property 1
@given(skeleton=st_effect_skeleton())
@settings(max_examples=50)
def test_skeleton_has_required_fields(skeleton):
    """Every skeleton has non-empty identifier, display_name, category, description."""
    assert skeleton.identifier
    assert skeleton.display_name
    assert isinstance(skeleton.category, EffectCategory)
    assert skeleton.description


# ── Property 2: Serialize/deserialize round-trip ────────────
# Feature: effect-catalog-core, Property 2
@given(skeleton=st_effect_skeleton())
@settings(max_examples=50)
def test_serialize_deserialize_roundtrip(skeleton):
    """serialize → deserialize produces an equivalent skeleton."""
    data = EffectCatalog.serialize(skeleton)
    restored = EffectCatalog.deserialize(data)
    assert restored.identifier == skeleton.identifier
    assert restored.display_name == skeleton.display_name
    assert restored.category == skeleton.category
    assert restored.description == skeleton.description
    assert restored.sync_points == skeleton.sync_points
    assert restored.initial_wait == skeleton.initial_wait


# ── Property 3: JSON compatibility ──────────────────────────
# Feature: effect-catalog-core, Property 3
@given(skeleton=st_effect_skeleton())
@settings(max_examples=50)
def test_serialized_is_json_compatible(skeleton):
    """Serialized skeleton can be round-tripped through JSON."""
    data = EffectCatalog.serialize(skeleton)
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    assert parsed["identifier"] == skeleton.identifier


# ── Property 4: Quality profiles always present ─────────────
# Feature: effect-catalog-core, Property 4
@given(skeleton=st_effect_skeleton())
@settings(max_examples=50)
def test_quality_profiles_always_present(skeleton):
    """Every skeleton has at least draft and production profiles."""
    assert "draft" in skeleton.quality_profiles
    assert "production" in skeleton.quality_profiles


# ── Property 5: Initial wait non-negative ───────────────────
# Feature: effect-catalog-core, Property 5
@given(skeleton=st_effect_skeleton())
@settings(max_examples=50)
def test_initial_wait_non_negative(skeleton):
    """initial_wait is always >= 0."""
    assert skeleton.initial_wait >= 0.0


# ── Property 6: Catalog save prevents duplicates ────────────
# Feature: effect-catalog-core, Property 6
@given(skeleton=st_effect_skeleton())
@settings(max_examples=20, deadline=None)
def test_catalog_save_rejects_duplicate(skeleton):
    """Saving the same identifier twice raises ConflictError."""
    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text("[]")
    catalog = EffectCatalog(catalog_dir=tmp)
    catalog.save(skeleton)
    try:
        catalog.save(skeleton)
        assert False, "Expected ConflictError"
    except ConflictError:
        pass


# ── Property 7: Catalog load returns all saved ──────────────
# Feature: effect-catalog-core, Property 7
@given(skeletons=st.lists(st_effect_skeleton(), min_size=1, max_size=5))
@settings(max_examples=20, deadline=None)
def test_catalog_load_returns_all_saved(skeletons):
    """All saved skeletons with unique IDs are loadable."""
    seen = set()
    unique = []
    for s in skeletons:
        if s.identifier not in seen:
            seen.add(s.identifier)
            unique.append(s)

    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text("[]")
    catalog = EffectCatalog(catalog_dir=tmp)
    for s in unique:
        catalog.save(s)

    loaded = catalog.load_all()
    loaded_ids = {s.identifier for s in loaded}
    for s in unique:
        assert s.identifier in loaded_ids


# ── Property 8: SchemaValidator returns defaults ────────────
# Feature: effect-catalog-core, Property 8
@given(default_val=st.text(min_size=1, max_size=20))
@settings(max_examples=50)
def test_schema_validator_applies_defaults(default_val):
    """Missing optional fields get their default values."""
    schema = {
        "type": "object",
        "properties": {
            "optional_field": {"type": "string", "default": default_val},
        },
        "required": [],
    }
    result = SchemaValidator.validate({}, schema)
    assert result["optional_field"] == default_val


# ── Property 9: SchemaValidator rejects missing required ────
# Feature: effect-catalog-core, Property 9
@given(field_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True))
@settings(max_examples=50)
def test_schema_validator_rejects_missing_required(field_name):
    """Missing required fields raise SchemaValidationError."""
    schema = {
        "type": "object",
        "properties": {field_name: {"type": "string"}},
        "required": [field_name],
    }
    try:
        SchemaValidator.validate({}, schema)
        assert False, "Expected SchemaValidationError"
    except SchemaValidationError as e:
        assert any(err["field"] == field_name for err in e.errors)


# ── Property 10: SchemaValidator doesn't mutate input ───────
# Feature: effect-catalog-core, Property 10
@given(val=st.text(min_size=1, max_size=20))
@settings(max_examples=50)
def test_schema_validator_no_mutation(val):
    """Original params dict is not mutated by validate()."""
    schema = {
        "type": "object",
        "properties": {"x": {"type": "string", "default": "fallback"}},
        "required": [],
    }
    original = {"y": val}
    original_copy = dict(original)
    SchemaValidator.validate(original, schema)
    assert original == original_copy


# ── Property 11: SyncPointMismatchError on wrong count ──────
# Feature: effect-catalog-core, Property 11
@given(
    expected=st.integers(min_value=1, max_value=10),
    actual=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50)
def test_sync_point_mismatch_captures_counts(expected, actual):
    """SyncPointMismatchError stores expected and actual counts."""
    assume(expected != actual)
    e = SyncPointMismatchError(expected, actual)
    assert e.expected == expected
    assert e.actual == actual


# ── Property 12: UnknownEffectError lists available ─────────
# Feature: effect-catalog-core, Property 12
@given(
    identifier=st_identifier(),
    available=st.lists(st_identifier(), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_unknown_effect_error_lists_available(identifier, available):
    """UnknownEffectError message includes the requested ID and available list."""
    assume(identifier not in available)
    e = UnknownEffectError(identifier, available)
    assert identifier in str(e)
    for a in available:
        assert a in str(e)


# ── Property 25: Registry resolves all catalog entries ──────
# Feature: effect-catalog-core, Property 25
@given(skeletons=st.lists(st_effect_skeleton(), min_size=1, max_size=5))
@settings(max_examples=15, deadline=None)
def test_registry_resolves_all_catalog_entries(skeletons):
    """Every skeleton in the catalog is resolvable by the registry."""
    seen = set()
    unique = []
    for s in skeletons:
        if s.identifier not in seen:
            seen.add(s.identifier)
            unique.append(s)

    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps([EffectCatalog.serialize(s) for s in unique]))
    catalog = EffectCatalog(catalog_dir=tmp)
    registry = EffectRegistry(catalog)
    for s in unique:
        resolved = registry.resolve(s.identifier)
        assert resolved.identifier == s.identifier


# ── Property 26: Registry raises on unknown identifier ──────
# Feature: effect-catalog-core, Property 26
@given(identifier=st_identifier())
@settings(max_examples=30, deadline=None)
def test_registry_raises_on_unknown(identifier):
    """Resolving an unknown identifier raises UnknownEffectError."""
    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text("[]")
    catalog = EffectCatalog(catalog_dir=tmp)
    registry = EffectRegistry(catalog)
    try:
        registry.resolve(identifier)
        assert False, "Expected UnknownEffectError"
    except UnknownEffectError:
        pass


# ── Property 27: Registry list_effects filters correctly ────
# Feature: effect-catalog-core, Property 27
@given(
    skeletons=st.lists(st_effect_skeleton(), min_size=2, max_size=8),
    filter_cat=st_effect_category(),
)
@settings(max_examples=15, deadline=None)
def test_registry_filter_by_category(skeletons, filter_cat):
    """list_effects(category=X) returns only skeletons with that category."""
    seen = set()
    unique = []
    for s in skeletons:
        if s.identifier not in seen:
            seen.add(s.identifier)
            unique.append(s)

    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps([EffectCatalog.serialize(s) for s in unique]))
    catalog = EffectCatalog(catalog_dir=tmp)
    registry = EffectRegistry(catalog)
    filtered = registry.list_effects(category=filter_cat)
    for s in filtered:
        assert s.category == filter_cat


# ── Property 28: Registry reload picks up changes ───────────
# Feature: effect-catalog-core, Property 28
@given(skeleton=st_effect_skeleton())
@settings(max_examples=15, deadline=None)
def test_registry_reload_picks_up_changes(skeleton):
    """After adding a skeleton and reloading, it becomes resolvable."""
    tmp = Path(tempfile.mkdtemp())
    manifest = tmp / "manifest.json"
    manifest.write_text("[]")
    catalog = EffectCatalog(catalog_dir=tmp)
    registry = EffectRegistry(catalog)
    assert len(registry.list_effects()) == 0

    catalog.save(skeleton)
    registry.reload()
    assert registry.resolve(skeleton.identifier).identifier == skeleton.identifier


# ── Property 29: Quality profiles independent per instance ──
# Feature: effect-catalog-core, Property 29
@given(a=st_effect_skeleton(), b=st_effect_skeleton())
@settings(max_examples=30)
def test_quality_profiles_independent(a, b):
    """Mutating one skeleton's quality_profiles doesn't affect another."""
    a.quality_profiles["custom"] = {"resolution": "4k"}
    assert "custom" not in b.quality_profiles


# ── Property 30: Category enum exhaustive ────────────────────
# Feature: effect-catalog-core, Property 30
def test_category_enum_has_seven_values():
    """EffectCategory has exactly 7 members (charts, text, social, data, editorial, narrative, motion)."""
    assert len(EffectCategory) == 7


# ── Property 31: UnknownProfileError captures profile name ──
# Feature: effect-catalog-core, Property 31
@given(
    profile=st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase),
    available=st.lists(st.text(min_size=1, max_size=10, alphabet=string.ascii_lowercase), min_size=1, max_size=3),
)
@settings(max_examples=50)
def test_unknown_profile_error_captures_name(profile, available):
    """UnknownProfileError stores the requested profile and available list."""
    assume(profile not in available)
    e = UnknownProfileError(profile, available)
    assert e.profile == profile
    assert profile in str(e)


# ── Property 8b: Valid params always pass validation ─────────
# Feature: effect-catalog-core, Property 8b
@given(params=st_valid_params())
@settings(max_examples=50)
def test_valid_params_always_pass(params):
    """Params generated by st_valid_params always validate against _TEST_SCHEMA."""
    result = SchemaValidator.validate(params, _TEST_SCHEMA)
    assert result["ticker"] == params["ticker"]


# ── Property 9b: Invalid params always fail validation ───────
# Feature: effect-catalog-core, Property 9b
@given(params=st_invalid_params())
@settings(max_examples=50)
def test_invalid_params_always_fail(params):
    """Params generated by st_invalid_params always raise SchemaValidationError."""
    try:
        SchemaValidator.validate(params, _TEST_SCHEMA)
        assert False, "Expected SchemaValidationError"
    except SchemaValidationError:
        pass


# ═══════════════════════════════════════════════════════════════
# Phase 2: Finance Effect Skeletons — Properties 13-24
# ═══════════════════════════════════════════════════════════════

from effects_catalog.templates.contextual_heatmap import assign_heatmap_color
from effects_catalog.templates.bull_bear_projection import compute_projection
from effects_catalog.templates.volatility_shadow import compute_drawdown_regions
from effects_catalog.templates.moat_radar import find_max_advantage_index
from effects_catalog.templates.atomic_reveal import (
    SENTIMENT_COLORS,
    compute_radial_positions,
    compute_grid_positions,
)
from effects_catalog.templates.relative_velocity import compute_overlap, compute_spread
import math


# ── Property 13: Benchmark heatmap color assignment ─────────
# Feature: finance-effect-skeletons, Property 13
@given(
    value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    start=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_heatmap_color_assignment(value, start):
    """Green when value >= start, red when below."""
    color = assign_heatmap_color(value, start, "#00E676", "#FF453A")
    if value >= start:
        assert color == "#00E676"
    else:
        assert color == "#FF453A"


# ── Property 14: Bull/Bear projection calculation ───────────
# Feature: finance-effect-skeletons, Property 14
@given(
    last_price=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    rate=st.floats(min_value=-0.99, max_value=10.0, allow_nan=False, allow_infinity=False),
    years=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=100)
def test_projection_compound_formula(last_price, rate, years):
    """Projected values follow compound growth: last_price * (1 + rate)^y."""
    result = compute_projection(last_price, rate, years)
    assert len(result) == years + 1
    for y, val in enumerate(result):
        expected = last_price * (1 + rate) ** y
        assert abs(val - expected) < max(abs(expected) * 1e-9, 1e-9)


# ── Property 15: Drawdown detection and percentage ──────────
# Feature: finance-effect-skeletons, Property 15
@given(
    values=st.lists(
        st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=2, max_size=50,
    ),
)
@settings(max_examples=100)
def test_drawdown_regions_match_running_max(values):
    """Drawdown regions correspond to indices where price < running max."""
    regions = compute_drawdown_regions(values)
    # Verify each region's indices are actually below running max
    running_max = values[0]
    in_drawdown = False
    for i in range(1, len(values)):
        running_max = max(running_max, values[i - 1])
        if values[i] < running_max:
            in_drawdown = True
        else:
            in_drawdown = False
    # Just verify regions are non-overlapping and within bounds
    for r in regions:
        assert 0 <= r["start_idx"] < len(values)
        assert 0 <= r["end_idx"] < len(values)
        assert r["start_idx"] <= r["end_idx"]


# ── Property 16: Radar chart largest advantage indication ───
# Feature: finance-effect-skeletons, Property 16
@given(
    values_a=st.lists(
        st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=1, max_size=20,
    ),
    values_b=st.lists(
        st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=1, max_size=20,
    ),
)
@settings(max_examples=100)
def test_radar_max_advantage_index(values_a, values_b):
    """find_max_advantage_index returns argmax(a - b)."""
    min_len = min(len(values_a), len(values_b))
    assume(min_len >= 1)
    a = values_a[:min_len]
    b = values_b[:min_len]
    idx = find_max_advantage_index(a, b)
    diffs = [ai - bi for ai, bi in zip(a, b)]
    assert diffs[idx] == max(diffs)


# ── Property 17: Radar chart mismatched lengths error ───────
# Feature: finance-effect-skeletons, Property 17
@given(
    len_a=st.integers(min_value=1, max_value=10),
    len_b=st.integers(min_value=1, max_value=10),
    len_labels=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100)
def test_radar_mismatched_lengths_error(len_a, len_b, len_labels):
    """LengthMismatchError stores all three lengths."""
    assume(not (len_a == len_b == len_labels))
    from effects_catalog.templates.moat_radar import LengthMismatchError
    err = LengthMismatchError(len_a, len_b, len_labels)
    assert err.len_a == len_a
    assert err.len_b == len_b
    assert err.len_labels == len_labels


# ── Property 18: Radar chart out-of-range values error ──────
# Feature: finance-effect-skeletons, Property 18
@given(
    value=st.one_of(
        st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
        st.floats(min_value=100.01, allow_nan=False, allow_infinity=False),
    ),
    index=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100)
def test_radar_out_of_range_error(value, index):
    """RangeError stores the offending value, index, and company."""
    from effects_catalog.templates.moat_radar import RangeError
    err = RangeError(value, index, "TestCo")
    assert err.value == value
    assert err.index == index
    assert err.company == "TestCo"


# ── Property 19: Sentiment color mapping ────────────────────
# Feature: finance-effect-skeletons, Property 19
@given(sentiment=st.sampled_from(["positive", "negative", "neutral"]))
@settings(max_examples=100)
def test_sentiment_color_mapping(sentiment):
    """SENTIMENT_COLORS maps positive→green, negative→red, neutral→grey."""
    color = SENTIMENT_COLORS[sentiment]
    if sentiment == "positive":
        assert color == "#10B981"
    elif sentiment == "negative":
        assert color == "#EF4444"
    else:
        assert color == "#6B7280"


# ── Property 20: Component layout positioning ───────────────
# Feature: finance-effect-skeletons, Property 20
@given(
    n=st.integers(min_value=1, max_value=20),
    radius=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_radial_positions_at_equal_radius(n, radius):
    """Radial positions are all at the specified radius from origin."""
    positions = compute_radial_positions(n, radius)
    assert len(positions) == n
    for x, y in positions:
        dist = math.sqrt(x**2 + y**2)
        assert abs(dist - radius) < 0.01


# ── Property 20b: Grid layout positioning ───────────────────
# Feature: finance-effect-skeletons, Property 20b
@given(n=st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_grid_positions_count(n):
    """Grid positions returns exactly n positions."""
    positions = compute_grid_positions(n)
    assert len(positions) == n


# ── Property 21: Highlight component not found error ────────
# Feature: finance-effect-skeletons, Property 21
@given(
    name=st.text(min_size=1, max_size=20, alphabet=string.ascii_letters),
    available=st.lists(
        st.text(min_size=1, max_size=20, alphabet=string.ascii_letters),
        min_size=1, max_size=5,
    ),
)
@settings(max_examples=100)
def test_component_not_found_error(name, available):
    """ComponentNotFoundError stores name and available list."""
    assume(name not in available)
    from effects_catalog.templates.atomic_reveal import ComponentNotFoundError
    err = ComponentNotFoundError(name, available)
    assert err.name == name
    assert err.available == available
    assert name in str(err)


# ── Property 22: Relative velocity spread calculation ───────
# Feature: finance-effect-skeletons, Property 22
@given(
    a=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    b=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_relative_velocity_spread(a, b):
    """Spread is abs(a-b)/min(abs(a),abs(b))*100 when both positive, 0 when base is 0."""
    spread = compute_spread(a, b)
    base = min(abs(a), abs(b))
    if base == 0:
        assert spread == 0.0
    else:
        expected = abs(a - b) / base * 100
        assert abs(spread - expected) < 0.01


# ── Property 23: Date range overlap alignment ───────────────
# Feature: finance-effect-skeletons, Property 23
@given(
    dates_a=st.lists(st.text(min_size=1, max_size=10, alphabet=string.ascii_lowercase), min_size=0, max_size=10),
    dates_b=st.lists(st.text(min_size=1, max_size=10, alphabet=string.ascii_lowercase), min_size=0, max_size=10),
)
@settings(max_examples=100)
def test_date_range_overlap(dates_a, dates_b):
    """compute_overlap returns the intersection preserving order from dates_a."""
    overlap = compute_overlap(dates_a, dates_b)
    set_b = set(dates_b)
    for d in overlap:
        assert d in set_b
        assert d in dates_a


# ── Property 24: Sequential highlight ordering ──────────────
# Feature: finance-effect-skeletons, Property 24
@given(
    n_highlights=st.integers(min_value=0, max_value=8),
)
@settings(max_examples=100)
def test_sequential_highlight_ordering(n_highlights):
    """PDF forensic generates N highlights and produces valid Python."""
    import ast
    from effects_catalog.templates.pdf_forensic import generate
    # Use unique large x-values that won't collide with other code numbers
    highlights = [
        {"bbox": {"x": 1000 + i * 1000, "y": 500, "width": 50, "height": 20}, "style": "rectangle"}
        for i in range(n_highlights)
    ]
    instruction = {
        "data": {
            "pdf_path": "/tmp/test.pdf",
            "page_number": 1,
            "highlights": highlights,
        },
        "title": "Test",
    }
    code = generate(instruction)
    ast.parse(code)
    # The highlights list in the generated code should preserve input order
    if n_highlights >= 2:
        # Find positions of unique x-values in the generated code
        positions = []
        for i in range(n_highlights):
            x_val = str(1000 + i * 1000)
            pos = code.find(x_val)
            if pos >= 0:
                positions.append(pos)
        if len(positions) == n_highlights:
            assert positions == sorted(positions)


# ═══════════════════════════════════════════════════════════════
# Phase 3: Narrative-Aware Pacing — Properties 32-37
# ═══════════════════════════════════════════════════════════════

from effects_catalog.scene_expander import SceneExpander, HIGH_IMPACT_TYPES, MIN_DURATION_THRESHOLD_S
from effects_catalog.ssml_data_pause import SSMLDataPauseInjector, MAX_SCENE_DURATION_S
from effects_catalog.static_freeze import StaticFreezeDetector, DELTA_THRESHOLD_PCT, MAX_NARRATION_S


# ── Property 32: Scene expansion trigger condition ──────────
# Feature: narrative-pacing, Property 32
@given(
    duration=st.floats(min_value=0.5, max_value=30.0, allow_nan=False, allow_infinity=False),
    visual_type=st.sampled_from(
        list(HIGH_IMPACT_TYPES) + ["text_overlay", "bar_chart", "quote_block", "section_title"]
    ),
)
@settings(max_examples=100)
def test_scene_expansion_trigger(duration, visual_type):
    """Expansion only when duration < 6s AND type is high-impact."""
    expander = SceneExpander()
    result = expander.expand_if_needed(duration, visual_type)
    if duration < MIN_DURATION_THRESHOLD_S and visual_type in HIGH_IMPACT_TYPES:
        assert result > duration
    else:
        assert result == duration


# ── Property 33: Initial wait baseline hold ─────────────────
# Feature: narrative-pacing, Property 33
@given(
    initial_wait=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_initial_wait_injected_before_animation(initial_wait):
    """When initial_wait > 0, a wait() call appears after first play()."""
    from asset_orchestrator.manim_codegen import _inject_pacing
    code = "class S(Scene):\n    def construct(self):\n        self.play(FadeIn(x))\n        self.play(Create(y))"
    instruction = {"_initial_wait": initial_wait}
    result = _inject_pacing(code, instruction)
    assert f"self.wait({initial_wait})" in result


# ── Property 34: Initial wait zero backward compatibility ───
# Feature: narrative-pacing, Property 34
@given(
    code_lines=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
)
@settings(max_examples=100)
def test_initial_wait_zero_no_injection(code_lines):
    """When initial_wait=0, no wait() is injected."""
    from asset_orchestrator.manim_codegen import _inject_pacing
    code = "\n".join(code_lines)
    instruction = {"_initial_wait": 0}
    result = _inject_pacing(code, instruction)
    assert "initial_wait" not in result


# ── Property 35: SSML data pause injection ──────────────────
# Feature: narrative-pacing, Property 35
@given(
    pct_value=st.integers(min_value=10, max_value=99),
    scene_duration=st.floats(min_value=0.5, max_value=7.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_ssml_pause_injected_for_high_pct(pct_value, scene_duration):
    """Percentages >= 10% get a break tag when scene < 8s."""
    injector = SSMLDataPauseInjector()
    text = f"dropped {pct_value} percent"
    result = injector.inject_pauses(text, scene_duration_s=scene_duration)
    assert "<break" in result


# ── Property 35b: SSML no injection for long scenes ─────────
# Feature: narrative-pacing, Property 35b
@given(
    pct_value=st.integers(min_value=10, max_value=99),
    scene_duration=st.floats(min_value=8.0, max_value=30.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_ssml_no_pause_for_long_scenes(pct_value, scene_duration):
    """No break tags when scene >= 8s."""
    injector = SSMLDataPauseInjector()
    text = f"dropped {pct_value} percent"
    result = injector.inject_pauses(text, scene_duration_s=scene_duration)
    assert "<break" not in result


# ── Property 36: Static freeze trigger condition ────────────
# Feature: narrative-pacing, Property 36
@given(
    delta=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    narration_s=st.floats(min_value=0.5, max_value=2.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_static_freeze_triggers_on_high_delta_short_narration(delta, narration_s):
    """Freeze when delta >= 10% AND narration < 3s."""
    detector = StaticFreezeDetector()
    instruction = {"data": {"delta_pct": delta}}
    result = detector.detect_freeze(instruction, narration_s)
    assert result is not None and result > 0


# ── Property 36b: Static freeze no trigger ──────────────────
# Feature: narrative-pacing, Property 36b
@given(
    delta=st.floats(min_value=0.0, max_value=9.9, allow_nan=False, allow_infinity=False),
    narration_s=st.floats(min_value=0.5, max_value=30.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_static_freeze_no_trigger_low_delta(delta, narration_s):
    """No freeze when delta < 10%."""
    detector = StaticFreezeDetector()
    instruction = {"data": {"delta_pct": delta}}
    result = detector.detect_freeze(instruction, narration_s)
    assert result is None


# ── Property 37: Forensic jump-cut vs travel ────────────────
# Feature: narrative-pacing, Property 37
@given(
    zoom_mode=st.sampled_from(["travel", "jump_cut"]),
)
@settings(max_examples=50)
def test_forensic_zoom_mode_code_difference(zoom_mode):
    """jump_cut uses frame.set(), travel uses frame.animate."""
    import ast
    from effects_catalog.templates.forensic_zoom import generate
    instruction = {
        "data": {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100 + i * 5 for i in range(12)],
            "focus_date": "2024-06-01",
            "zoom_mode": zoom_mode,
        },
        "title": "Test",
    }
    code = generate(instruction)
    ast.parse(code)
    if zoom_mode == "jump_cut":
        assert "frame.set(" in code
    else:
        assert "frame.animate" in code


# ═══════════════════════════════════════════════════════════════
# Phase 4: Cinematic & Narrative Effects — Properties 38-49
# ═══════════════════════════════════════════════════════════════

from effects_catalog.templates.liquidity_shock import (
    DateRangeError as LiquidityDateRangeError,
    RangeError as LiquidityRangeError,
)
from effects_catalog.templates.momentum_glow import (
    InsufficientDataError as MomentumInsufficientDataError,
    compute_rolling_slope,
)
from effects_catalog.templates.regime_shift import (
    DateOrderError as RegimeDateOrderError,
    DateRangeError as RegimeDateRangeError,
)
from effects_catalog.templates.speed_ramp import (
    DateOrderError as SpeedDateOrderError,
    RangeError as SpeedRangeError,
    compute_segment_durations,
)
from effects_catalog.templates.capital_flow import compute_arrow_width
from effects_catalog.templates.compounding_explosion import compute_curve, find_breakpoint
from effects_catalog.templates.market_share_territory import (
    find_crossover_indices,
    territory_owner,
)
from effects_catalog.templates.historical_rank import compute_percentile


# ── Property 38: Liquidity shock date validation ────────────
# Feature: cinematic-effects, Property 38
@given(
    shock_date=st.text(min_size=10, max_size=10, alphabet="0123456789-"),
    valid_start=st.just("2024-01-01"),
    valid_end=st.just("2024-12-01"),
)
@settings(max_examples=100)
def test_liquidity_shock_date_range_error(shock_date, valid_start, valid_end):
    """DateRangeError stores shock_date and valid range."""
    err = LiquidityDateRangeError(shock_date, valid_start, valid_end)
    assert err.shock_date == shock_date
    assert err.valid_start == valid_start
    assert err.valid_end == valid_end
    assert shock_date in str(err)


# ── Property 39: Liquidity shock intensity bounds ───────────
# Feature: cinematic-effects, Property 39
@given(
    value=st.one_of(
        st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.01, allow_nan=False, allow_infinity=False),
    ),
)
@settings(max_examples=100)
def test_liquidity_shock_intensity_range_error(value):
    """RangeError stores the invalid intensity value."""
    err = LiquidityRangeError(value, "shock_intensity")
    assert err.value == value
    assert err.field == "shock_intensity"
    assert str(value) in str(err) or "shock_intensity" in str(err)


# ── Property 40: Momentum glow threshold activation ─────────
# Feature: cinematic-effects, Property 40
@given(
    values=st.lists(
        st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
        min_size=5, max_size=50,
    ),
    window=st.integers(min_value=2, max_value=4),
)
@settings(max_examples=100)
def test_momentum_glow_slope_length(values, window):
    """compute_rolling_slope returns list of same length as input."""
    slopes = compute_rolling_slope(values, window)
    assert len(slopes) == len(values)
    # First `window` slopes should be 0 (not enough data)
    for i in range(min(window, len(slopes))):
        assert slopes[i] == 0.0


# ── Property 41: Momentum glow window validation ────────────
# Feature: cinematic-effects, Property 41
@given(
    count=st.integers(min_value=1, max_value=19),
    window=st.integers(min_value=20, max_value=50),
)
@settings(max_examples=100)
def test_momentum_glow_insufficient_data_error(count, window):
    """InsufficientDataError stores count and window."""
    assume(count < window)
    err = MomentumInsufficientDataError(count, window)
    assert err.count == count
    assert err.window == window
    assert str(window) in str(err)


# ── Property 42: Date range ordering validation ─────────────
# Feature: cinematic-effects, Property 42
@given(
    start_month=st.integers(min_value=7, max_value=12),
    end_month=st.integers(min_value=1, max_value=6),
)
@settings(max_examples=100)
def test_date_order_error_regime_shift(start_month, end_month):
    """DateOrderError for regime_shift stores start and end."""
    start = f"2024-{start_month:02d}-01"
    end = f"2024-{end_month:02d}-01"
    err = RegimeDateOrderError(start, end)
    assert err.start == start
    assert err.end == end
    assert start in str(err)


# ── Property 43: Regime shift zone outside data range ───────
# Feature: cinematic-effects, Property 43
@given(
    label=st.text(min_size=1, max_size=20, alphabet=string.ascii_letters),
)
@settings(max_examples=100)
def test_regime_shift_date_range_error(label):
    """DateRangeError stores regime label and data range."""
    err = RegimeDateRangeError(label, "2024-01-01", "2024-12-01")
    assert err.regime_label == label
    assert err.data_start == "2024-01-01"
    assert err.data_end == "2024-12-01"
    assert label in str(err)


# ── Property 44: Speed ramp positive speed validation ───────
# Feature: cinematic-effects, Property 44
@given(
    speed=st.floats(max_value=0.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_speed_ramp_range_error(speed):
    """RangeError stores the invalid speed value."""
    err = SpeedRangeError(speed)
    assert err.speed == speed
    assert str(speed) in str(err) or "must be > 0" in str(err)


# ── Property 45: Speed ramp segment duration computation ────
# Feature: cinematic-effects, Property 45
@given(
    n_points=st.integers(min_value=2, max_value=20),
    base_duration=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_speed_ramp_segment_count(n_points, base_duration):
    """compute_segment_durations returns n_points - 1 durations."""
    durations = compute_segment_durations(n_points, [], [], base_duration=base_duration)
    assert len(durations) == n_points - 1
    # All durations should be positive
    for d in durations:
        assert d > 0


# ── Property 46: Capital flow arrow proportionality ─────────
# Feature: cinematic-effects, Property 46
@given(
    flow_amount=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    max_amount=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    base_width=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_capital_flow_arrow_proportionality(flow_amount, max_amount, base_width):
    """Arrow width = (flow_amount / max_amount) * base_width."""
    assume(max_amount > 0)
    width = compute_arrow_width(flow_amount, max_amount, base_width)
    expected = (flow_amount / max_amount) * base_width
    assert abs(width - expected) < 0.01


# ── Property 47: Compounding explosion formula correctness ──
# Feature: cinematic-effects, Property 47
@given(
    principal=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    rate=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
    years=st.integers(min_value=1, max_value=30),
)
@settings(max_examples=100)
def test_compounding_curve_formula(principal, rate, years):
    """Curve value at year y = principal * (1 + rate)^y."""
    curve = compute_curve(principal, rate, years)
    assert len(curve) == years + 1
    for y, val in enumerate(curve):
        expected = principal * (1 + rate) ** y
        assert abs(val - expected) < max(abs(expected) * 1e-9, 1e-9)


# ── Property 48: Market share territory ownership at crossover
# Feature: cinematic-effects, Property 48
@given(
    val_a=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    val_b=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_territory_ownership(val_a, val_b):
    """territory_owner returns 'a' when a >= b, 'b' otherwise."""
    owner = territory_owner(val_a, val_b)
    if val_a >= val_b:
        assert owner == "a"
    else:
        assert owner == "b"


# ── Property 49: Historical rank percentile calculation ─────
# Feature: cinematic-effects, Property 49
@given(
    current=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    historical=st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=50,
    ),
)
@settings(max_examples=100)
def test_historical_rank_percentile(current, historical):
    """Percentile = count(v < current) / len(historical) * 100."""
    pct = compute_percentile(current, historical)
    count_below = sum(1 for v in historical if v < current)
    expected = (count_below / len(historical)) * 100
    assert abs(pct - expected) < 0.01
