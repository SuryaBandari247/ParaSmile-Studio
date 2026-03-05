# Tasks: Effect Catalog Core

## Task 1: Core Data Models
- [x] Create `effects_catalog/__init__.py` with `EffectSkeleton` dataclass (identifier, display_name, category, description, parameter_schema, preview_config, reference_video_path, template_module, sync_points, quality_profiles, initial_wait)
- [x] Create `EffectCategory` enum (CHARTS, TEXT, SOCIAL, DATA, EDITORIAL)
- [x] Create `effects_catalog/exceptions.py` with `UnknownEffectError`, `ConflictError`, `ValidationError`, `SyncPointMismatchError`, `UnknownProfileError`, `CatalogParseError`
- [x] Add unit tests in `tests/unit/test_effect_models.py`

**Requirements:** 1.1, 1.2, 1.5, 17.5, 18.1

## Task 2: SchemaValidator
- [x] Create `effects_catalog/schema_validator.py` with `SchemaValidator.validate(params, schema)` — validates against JSON Schema, returns params with defaults, raises ValidationError with field details
- [x] Add unit tests in `tests/unit/test_schema_validator.py`

**Requirements:** 1.6, 1.7

## Task 3: EffectCatalog Persistence
- [x] Create `effects_catalog/catalog.py` with `EffectCatalog` class — `load_all()`, `get_by_id()`, `save()`, `serialize()`, `deserialize()`
- [x] Create empty `effects_catalog/manifest.json`, `effects_catalog/templates/`, `effects_catalog/assets/` directories
- [x] Handle malformed JSON (CatalogParseError), missing templates (warn+skip), missing videos (non-fatal)
- [x] Add unit tests in `tests/unit/test_effect_catalog.py` — load, save, round-trip, conflict, malformed JSON

**Requirements:** 2.1, 2.2, 2.3, 2.5, 8.1, 8.2, 8.3, 8.4

## Task 4: EffectRegistry + LegacyMapper
- [x] Create `effects_catalog/registry.py` with `EffectRegistry` — `resolve()`, `list_effects()`, `list_aliases()`, `reload()`
- [x] Create `effects_catalog/legacy_mapper.py` with `LegacyMapper` — loads `legacy_mappings.json`, resolves aliases with sub-type dispatch, logs deprecation warnings
- [x] Create `effects_catalog/legacy_mappings.json` with data_chart → sub-type mappings
- [x] Add unit tests in `tests/unit/test_effect_registry.py` and `tests/unit/test_legacy_mapper.py`

**Requirements:** 3.1, 3.2, 3.3, 3.4, 3.5, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7

## Task 5: Migrate Existing Scene Types to Skeletons
- [x] Create manifest entries for all 17 existing scene types (text_overlay, bar_chart, line_chart, pie_chart, code_snippet, reddit_post, stat_callout, quote_block, section_title, bullet_reveal, comparison, fullscreen_statement, data_chart, timeseries, horizontal_bar, grouped_bar, donut)
- [x] For each, extract parameter schema from current codegen functions, set category, preview_config, default quality_profiles and initial_wait
- [x] Populate `effects_catalog/manifest.json` with all 17 entries
- [x] Add unit test verifying all 17 types are loadable and resolvable

**Requirements:** 2.6, 4.2

## Task 6: CodegenEngine Refactor
- [x] Refactor `generate_scene_code()` in `manim_codegen.py` to accept optional `registry`, `audio_timestamps`, `quality_profile` params
- [x] Implement registry-based dispatch: resolve → validate → merge styles → render template
- [x] Implement sync_point wait injection when audio_timestamps provided
- [x] Implement quality_profile selection and validation
- [x] Preserve legacy fallback when registry is None
- [x] Add unit tests in `tests/unit/test_codegen_engine.py` — backward compat, sync points, quality profiles, style merge

**Requirements:** 4.1, 4.2, 4.3, 4.4, 17.2, 17.3, 17.4, 18.4, 18.8

## Task 7: Effects API Router
- [x] Create `studio_api/routers/effects.py` with GET /api/effects, GET /api/effects/aliases, GET /api/effects/{identifier}, POST /api/effects
- [x] Add quality_profile query param to existing render endpoint in visuals router
- [x] Create Pydantic models: EffectSummary, EffectDetail, EffectCreateRequest, AliasListResponse
- [x] Register router in studio_api main app
- [x] Add unit tests in `tests/unit/test_effects_router.py`

**Requirements:** 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4, 18.6

## Task 8: Effects API Client (Frontend)
- [x] Create `frontend/src/api/effects.ts` with listEffects, getEffect, createEffect, getPreviewUrl
- [x] Add TypeScript types for EffectSummary, EffectDetail, EffectCreateRequest

**Requirements:** 5.1, 6.1

## Task 9: Effect Browser UI
- [x] Create `frontend/src/components/visual/EffectBrowser.tsx` — grid layout, category filter, video preview, parameter schema display, sync_point names, quality profile selector
- [x] Add "Apply to Scene" action that sets visual_type and visual_data
- [x] Integrate into VisualPanel as side panel or modal
- [x] Add legacy aliases section

**Requirements:** 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 17.6, 18.7, 19.7

## Task 10: Property-Based Tests (Core Properties 1-12, 25-31)
- [x] Create `tests/property/test_properties_effects.py` with Hypothesis tests for properties 1-12 and 25-31
- [x] Create custom generators: st_effect_skeleton(), st_valid_params(), st_invalid_params()
- [x] Each property test tagged with `# Feature: effect-catalog-core, Property N`

**Requirements:** Cross-cutting validation of all core requirements
