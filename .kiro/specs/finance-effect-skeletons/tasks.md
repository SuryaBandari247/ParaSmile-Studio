# Tasks: Finance Effect Skeletons

Depends on: effect-catalog-core (Tasks 1-5 must be complete)

## Task 1: PDF Forensic Effect
- [x] Create `effects_catalog/templates/pdf_forensic.py` — PDF page to image conversion (pdf2image/PyMuPDF), Manim scene with ImageMobject, MovingCameraScene zoom, sequential highlight animation
- [x] Add manifest entry with identifier "pdf_forensic", category "editorial", parameter schema (pdf_path, page_number, highlights with bbox/text_search, style, color, opacity)
- [x] Handle errors: invalid PDF path, page out of range, text search miss
- [x] Add unit tests in `tests/unit/test_pdf_forensic.py`

**Requirements:** 9.1-9.9

## Task 2: Forensic Zoom Effect
- [x] Create `effects_catalog/templates/forensic_zoom.py` — MovingCameraScene with camera dive to focus_date, SurroundingRectangle with glow_color, blur_opacity fade on non-focus regions
- [x] Add manifest entry with identifier "forensic_zoom", category "data", parameter schema (focus_date, focus_window_days, glow_color, blur_opacity, zoom_mode, wide_hold)
- [x] Handle errors: focus_date outside data range
- [x] Add unit tests in `tests/unit/test_forensic_zoom.py`

**Requirements:** 10.1-10.7

## Task 3: Volatility Shadow Effect
- [x] Create `effects_catalog/templates/volatility_shadow.py` — running max tracking, Polygon area fill between ATH line and price line, dynamic shadow growth/shrink, optional drawdown % label
- [x] Add manifest entry with identifier "volatility_shadow", category "data", parameter schema (shadow_color, shadow_opacity, show_drawdown_pct)
- [x] Handle errors: fewer than 2 data points
- [x] Add unit tests in `tests/unit/test_volatility_shadow.py`

**Requirements:** 11.1-11.8

## Task 4: Relative Velocity Comparison Effect
- [x] Create `effects_catalog/templates/relative_velocity.py` — dual timeseries with dynamic Arrow between series, DecimalNumber for percentage spread, continuous update tracking
- [x] Add manifest entry with identifier "relative_velocity", category "data", parameter schema (series_a_name, series_b_name, show_delta_arrow, delta_format, arrow_color)
- [x] Handle warnings: mismatched date ranges → align to overlap
- [x] Add unit tests in `tests/unit/test_relative_velocity.py`

**Requirements:** 12.1-12.8

## Task 5: Contextual Heatmap Effect
- [x] Create `effects_catalog/templates/contextual_heatmap.py` — Yahoo Finance benchmark fetch, Rectangle strip background layer, green/red color based on benchmark performance vs start
- [x] Add manifest entry with identifier "contextual_heatmap", category "data", parameter schema (benchmark_ticker, green_color, red_color, heatmap_opacity, benchmark_label)
- [x] Handle errors: invalid benchmark_ticker
- [x] Add unit tests in `tests/unit/test_contextual_heatmap.py`

**Requirements:** 13.1-13.10

## Task 6: Bull vs Bear Projection Effect
- [x] Create `effects_catalog/templates/bull_bear_projection.py` — historical line + "Today" marker, three DashedLine projections with compound growth, LaggedStart fan-out, end labels with projected price
- [x] Add manifest entry with identifier "bull_bear_projection", category "data", parameter schema (optimistic_rate, realistic_rate, pessimistic_rate, projection_years, projection_labels)
- [x] Handle errors: fewer than 2 data points
- [x] Add unit tests in `tests/unit/test_bull_bear_projection.py`

**Requirements:** 14.1-14.10

## Task 7: Moat Comparison Radar Effect
- [x] Create `effects_catalog/templates/moat_radar.py` — polar axes with N radial axes, two Polygon fills with partial opacity, sequential animation (axes → Company A → Company B), Indicate on max-advantage axis, legend
- [x] Add manifest entry with identifier "moat_radar", category "data", parameter schema (company_a_name, company_a_values, company_b_name, company_b_values, metric_labels, company_a_color, company_b_color)
- [x] Handle errors: mismatched list lengths, out-of-range values (0-100)
- [x] Add unit tests in `tests/unit/test_moat_radar.py`

**Requirements:** 15.1-15.10

## Task 8: Atomic Component Reveal Effect
- [x] Create `effects_catalog/templates/atomic_reveal.py` — central entity block, LaggedStart radial/grid component fly-out, sentiment color-coding (green/red/neutral), Indicate on highlight_component, value label fade-in
- [x] Add manifest entry with identifier "atomic_reveal", category "editorial", parameter schema (entity_name, components, highlight_component, layout)
- [x] Handle errors: highlight_component not in components list
- [x] Add unit tests in `tests/unit/test_atomic_reveal.py`

**Requirements:** 16.1-16.11

## Task 9: Property-Based Tests (Properties 13-24)
- [x] Add Hypothesis tests for properties 13-24 to `tests/property/test_properties_effects.py`
- [x] Custom generators for price series, value arrays, component lists, highlight regions
- [x] Each property test tagged with `# Feature: finance-effect-skeletons, Property N`

**Requirements:** Cross-cutting validation of all finance effect requirements
