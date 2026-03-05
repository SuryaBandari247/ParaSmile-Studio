# Tasks: Cinematic & Narrative Effects (Phase 4)

Depends on: effect-catalog-core (Tasks 1-6 must be complete)

## Task 1: Liquidity Shock Effect
- [x] Create `effects_catalog/templates/liquidity_shock.py` — vertical flash line at shock_date, ripple shockwave ring, camera micro-shake, brief price-line glow
- [x] Add manifest entry with identifier "liquidity_shock", category "narrative", parameter schema (shock_date, shock_color, shock_intensity, shock_label)
- [x] Handle errors: shock_date outside data range
- [x] Add unit tests in `tests/unit/test_liquidity_shock.py`

**Requirements:** 25.1-25.4

## Task 2: Momentum Glow Effect
- [x] Create `effects_catalog/templates/momentum_glow.py` — dynamic glow intensity/color on timeseries line based on rolling slope, neon trail for high-momentum, fade for cooling
- [x] Add manifest entry with identifier "momentum_glow", category "motion", parameter schema (momentum_window, glow_color_up, glow_color_down, glow_max_width, baseline_width)
- [x] Handle errors: fewer than momentum_window data points
- [x] Add unit tests in `tests/unit/test_momentum_glow.py`

**Requirements:** 26.1-26.4

## Task 3: Regime Shift Effect
- [x] Create `effects_catalog/templates/regime_shift.py` — labeled color-coded background zones on timeseries for economic eras, sequential zone reveal
- [x] Add manifest entry with identifier "regime_shift", category "narrative", parameter schema (regimes array with start_date/end_date/label/color, zone_opacity)
- [x] Handle errors: overlapping regime date ranges, dates outside data range
- [x] Add unit tests in `tests/unit/test_regime_shift.py`

**Requirements:** 27.1-27.4

## Task 4: Speed Ramp Effect
- [x] Create `effects_catalog/templates/speed_ramp.py` — variable playback speed across configurable time segments, fast-forward for boring periods, slow-mo for crashes
- [x] Add manifest entry with identifier "speed_ramp", category "motion", parameter schema (segments array with start_date/end_date/speed_multiplier, default_speed)
- [x] Handle errors: overlapping segments, speed_multiplier <= 0
- [x] Add unit tests in `tests/unit/test_speed_ramp.py`

**Requirements:** 28.1-28.4

## Task 5: Capital Flow Effect
- [x] Create `effects_catalog/templates/capital_flow.py` — animated directional arrows between labeled entities, arrow thickness proportional to flow amount, sequential flow reveal
- [x] Add manifest entry with identifier "capital_flow", category "narrative", parameter schema (flows array with from/to/amount/color, entity_positions, layout)
- [x] Handle errors: entity referenced in flow but not in entity list
- [x] Add unit tests in `tests/unit/test_capital_flow.py`

**Requirements:** 29.1-29.4

## Task 6: Compounding Explosion Effect
- [x] Create `effects_catalog/templates/compounding_explosion.py` — exponential growth curve with glow breakpoint where curve steepens, pulse + intensified line glow at threshold
- [x] Add manifest entry with identifier "compounding_explosion", category "narrative", parameter schema (growth_rate, breakpoint_year, glow_color, explosion_intensity)
- [x] Handle errors: growth_rate <= 0, breakpoint_year outside data range
- [x] Add unit tests in `tests/unit/test_compounding_explosion.py`

**Requirements:** 30.1-30.4

## Task 7: Market Share Territory Effect
- [x] Create `effects_catalog/templates/market_share_territory.py` — area fills between competing timeseries lines, color-coded territory ownership, dominance shift visualization
- [x] Add manifest entry with identifier "market_share_territory", category "data", parameter schema (series_a_name, series_b_name, territory_color_a, territory_color_b, territory_opacity)
- [x] Handle errors: mismatched date ranges → align to overlap
- [x] Add unit tests in `tests/unit/test_market_share_territory.py`

**Requirements:** 31.1-31.4

## Task 8: Historical Rank Effect
- [x] Create `effects_catalog/templates/historical_rank.py` — vertical percentile ladder with labeled bands, animated marker settling into position
- [x] Add manifest entry with identifier "historical_rank", category "data", parameter schema (current_value, historical_values, metric_label, percentile_bands)
- [x] Handle errors: empty historical_values, current_value outside historical range (clamp with warning)
- [x] Add unit tests in `tests/unit/test_historical_rank.py`

**Requirements:** 32.1-32.4

## Task 9: Property-Based Tests (Properties 38-49)
- [x] Add Hypothesis tests for properties 38-49 to `tests/property/test_properties_effects.py`
- [x] Custom generators for shock events, regime arrays, flow graphs, growth curves
- [x] Each property test tagged with `# Feature: cinematic-effects, Property N`

**Requirements:** Cross-cutting validation of all cinematic/narrative effect requirements
