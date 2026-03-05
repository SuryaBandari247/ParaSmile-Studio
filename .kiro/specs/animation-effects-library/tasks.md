# Tasks: Animation Effects Library (Parent)

This spec has been split into 3 implementation phases. See sub-specs for task lists:

## Phase 1: Effect Catalog Core (implement first)
#[[file:.kiro/specs/effect-catalog-core/tasks.md]]
- 10 tasks: data models, schema validator, catalog persistence, registry, legacy mapper, migrate 17 existing types, codegen refactor, API router, frontend API client, Effect Browser UI, property tests

## Phase 2: Finance Effect Skeletons (depends on Phase 1)
#[[file:.kiro/specs/finance-effect-skeletons/tasks.md]]
- 9 tasks: 8 new effect templates + property tests

## Phase 3: Narrative-Aware Pacing (depends on Phase 1, parallel with Phase 2)
#[[file:.kiro/specs/narrative-pacing/tasks.md]]
- 6 tasks: scene expander, initial wait, forensic slow-mo, SSML pause, static freeze, property tests

## Phase 4: Cinematic & Narrative Effects (depends on Phase 1, parallel with Phases 2-3)
#[[file:.kiro/specs/cinematic-effects/tasks.md]]
- 9 tasks: liquidity shock, momentum glow, regime shift, speed ramp, capital flow, compounding explosion, market share territory, historical rank, property tests
