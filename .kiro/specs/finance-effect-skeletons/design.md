# Design: Finance Effect Skeletons

Parent design: #[[file:.kiro/specs/animation-effects-library/design.md]]
Depends on: effect-catalog-core

Each effect is a self-contained skeleton: a manifest entry in `effects_catalog/manifest.json`, a Manim template in `effects_catalog/templates/`, and a reference video in `effects_catalog/assets/`. All effects use the EffectSkeleton dataclass, EffectCatalog, and EffectRegistry from the catalog core spec.

## Effects Summary

| Identifier | Category | Key Manim Techniques |
|---|---|---|
| pdf_forensic | editorial | ImageMobject, MovingCameraScene, SurroundingRectangle |
| forensic_zoom | data | MovingCameraScene, camera.frame.animate, SurroundingRectangle with glow |
| volatility_shadow | data | Polygon area fill, running max tracking, DecimalNumber for drawdown % |
| relative_velocity | data | DynamicDelta VGroup, Arrow, DecimalNumber, dual-line Create |
| contextual_heatmap | data | Rectangle strips behind axes, Yahoo Finance enrichment |
| bull_bear_projection | data | DashedLine, compound growth calc, LaggedStart fan-out |
| moat_radar | data | Polar axes, Polygon fill, Indicate on max-advantage axis |
| atomic_reveal | editorial | LaggedStart, radial/grid positioning, sentiment color-coding, Indicate |

## Parameter Schemas

All parameter schemas are defined in the parent design doc under "New Effect Parameter Schemas".

## Correctness Properties

Properties 13-24 from the parent design cover these effects:
- 13: Benchmark heatmap color assignment
- 14: Bull/Bear projection calculation
- 15: Drawdown detection and percentage
- 16: Radar largest advantage indication
- 17: Radar mismatched lengths error
- 18: Radar out-of-range values error
- 19: Sentiment color mapping
- 20: Component layout positioning
- 21: Highlight component not found error
- 22: Relative velocity arrow direction
- 23: Date range overlap alignment
- 24: Sequential highlight ordering
