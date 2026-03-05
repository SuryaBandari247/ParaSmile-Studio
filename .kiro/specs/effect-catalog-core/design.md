# Design: Effect Catalog Core

Parent design: #[[file:.kiro/specs/animation-effects-library/design.md]]

This design covers Components 1-9 and 4a from the parent design document:

1. EffectSkeleton (dataclass with sync_points, quality_profiles, initial_wait)
2. EffectCategory (enum)
3. EffectCatalog (persistence — manifest.json + templates/ + assets/)
4. EffectRegistry (runtime lookup with LegacyMapper)
4a. LegacyMapper (alias table — legacy_mappings.json)
5. CodegenEngine (refactored manim_codegen.py with sync_points, quality_profile, initial_wait)
6. SchemaValidator
7. Effects API Router (GET /api/effects, GET /api/effects/aliases, GET /api/effects/{id}, POST /api/effects)
8. EffectBrowser (React component)
9. Effects API Client (TypeScript)

Correctness Properties covered: 1-12, 25-31 from the parent design.

All component interfaces, data models, error handling, and testing strategy are defined in the parent design doc.
