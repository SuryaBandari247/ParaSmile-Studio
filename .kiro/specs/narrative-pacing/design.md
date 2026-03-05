# Design: Narrative-Aware Pacing

Parent design: #[[file:.kiro/specs/animation-effects-library/design.md]]
Depends on: effect-catalog-core

This design covers Components 10-14 and the Pacing Layer Summary from the parent design document:

10. SceneExpander (orchestrator layer — auto-pads short high-impact scenes)
11. InitialWait (codegen layer — baseline hold before primary animation)
12. ForensicSlowMo (codegen layer — jump-cut zoom mode for forensic_zoom)
13. SSMLDataPauseInjector (audio layer — break tags after high-impact phrases)
14. StaticFreezeDetector (codegen layer — 2s hold for high-delta fast narration)

## Pacing Layer Summary

| Layer | Component | Trigger | Effect | Default |
|---|---|---|---|---|
| Audio | SSMLDataPauseInjector | ≥10% delta or ≥$1B in narration text | Inserts `<break>` after phrase, extends audio duration | 1000ms pause |
| Orchestrator | SceneExpander | narration < 6s AND high-impact visual type | Extends target_duration with padding | +2.5s pad |
| Codegen | InitialWait | data/timeseries effects | Holds baseline before primary animation | 1.5s hold |
| Codegen | StaticFreezeDetector | ≥10% delta AND narration < 3s | Appends static hold at end of render | 2.0s freeze |
| Codegen | ForensicSlowMo | forensic_zoom with zoom_mode=jump_cut | Instant camera transition, reclaims transit time | 1.0s wide_hold |

## Correctness Properties

Properties 32-37 from the parent design:
- 32: Scene expansion trigger condition
- 33: Initial wait baseline hold
- 34: Initial wait zero backward compatibility
- 35: SSML data pause injection
- 36: Static freeze trigger condition
- 37: Forensic jump-cut time savings

All component interfaces, env var configs, and error handling are defined in the parent design doc.
