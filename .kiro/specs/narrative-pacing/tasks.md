# Tasks: Narrative-Aware Pacing

Depends on: effect-catalog-core (Tasks 1-6 must be complete)

## Task 1: SceneExpander
- [x] Create `effects_catalog/scene_expander.py` with `SceneExpander` class — `expand_if_needed(narration_duration_s, visual_type, style_overrides)` returns final target_duration
- [x] HIGH_IMPACT_TYPES: data_chart, timeseries, forensic_zoom, volatility_shadow, bull_bear_projection
- [x] Reads SCENE_EXPANSION_PAD_S from env (default 2.5), overridable via style_overrides["expansion_pad_s"]
- [x] Threshold: only expands when narration < 6.0s
- [x] Logs original duration, expansion amount, final duration
- [x] Integrate into visual_service.py render flow (after audio duration known, before codegen)
- [x] Add unit tests in `tests/unit/test_scene_expander.py`

**Requirements:** 20.1, 20.2, 20.3, 20.4, 20.5

## Task 2: InitialWait Integration
- [x] Add initial_wait support to CodegenEngine template rendering — generates `self.wait(initial_wait)` before primary animation
- [x] Default initial_wait: 1.5s for data/timeseries effects, 0 for text effects (set in manifest entries)
- [x] Overridable via style_overrides["initial_wait"]
- [x] When initial_wait=0, no wait() generated (backward compat)
- [x] Add unit tests in `tests/unit/test_initial_wait.py`

**Requirements:** 21.1, 21.2, 21.3, 21.4, 21.5

## Task 3: Forensic SlowMo (Jump-Cut Zoom)
- [x] Add zoom_mode ("travel"/"jump_cut") and wide_hold params to forensic_zoom template
- [x] jump_cut mode: display wide chart for wide_hold seconds, then instant camera.frame.move_to() — no animation frames
- [x] travel mode: smooth camera pan (original behavior)
- [x] Jump-cut reclaims ≥1.5s of visual time vs travel
- [x] Add unit tests in `tests/unit/test_forensic_slowmo.py`

**Requirements:** 22.1, 22.2, 22.3, 22.4, 22.5

## Task 4: SSMLDataPauseInjector
- [x] Create `effects_catalog/ssml_data_pause.py` with `SSMLDataPauseInjector` class
- [x] Regex patterns: PCT_PATTERN for ≥10% values, CURRENCY_PATTERN for ≥$1B values
- [x] `inject_pauses(narration_text, scene_duration_s, data_pause_ms)` returns text with `<break>` tags
- [x] Reads DATA_PAUSE_MS from env (default 1000), overridable per-scene
- [x] Skips injection when scene_duration_s ≥ 8.0s
- [x] Logs each detected phrase and pause duration
- [x] Integrate into voice_synthesizer or audio_service preprocessing
- [x] Add unit tests in `tests/unit/test_ssml_data_pause.py`

**Requirements:** 23.1, 23.2, 23.3, 23.4, 23.5, 23.6

## Task 5: StaticFreezeDetector
- [x] Create `effects_catalog/static_freeze.py` with `StaticFreezeDetector` class
- [x] `detect_freeze(instruction, narration_duration_s, style_overrides)` returns freeze_duration or None
- [x] `extract_delta(instruction)` inspects events, annotations, chart metadata for percentage deltas
- [x] Trigger: abs(delta) ≥ 10% AND narration < 3.0s
- [x] Reads STATIC_FREEZE_S from env (default 2.0), overridable via style_overrides["freeze_duration_s"]
- [x] Integrate into CodegenEngine — appends `self.wait(freeze_s)` at end of generated code
- [x] Logs detected delta, narration duration, freeze duration
- [x] Add unit tests in `tests/unit/test_static_freeze.py`

**Requirements:** 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7

## Task 6: Property-Based Tests (Properties 32-37)
- [x] Add Hypothesis tests for properties 32-37 to `tests/property/test_properties_effects.py`
- [x] Custom generators for duration/type combos, narration text with data phrases, delta/narration combos
- [x] Each property test tagged with `# Feature: narrative-pacing, Property N`

**Requirements:** Cross-cutting validation of all pacing requirements
