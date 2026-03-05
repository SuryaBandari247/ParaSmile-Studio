# Requirements Document

## Introduction

The Animation Effects Library transforms the current monolithic, hardcoded Manim codegen system into a cataloged, reusable library of animation effect skeletons. Each effect (e.g., timeseries with camera tracking, bar chart with progressive reveal, stat callout with indicator highlight) becomes a registered, parameterized component that can be browsed in the UI, applied to new videos, and extended over time. The library grows organically as new effects are developed for specific videos and then generalized into reusable skeletons.

## Glossary

- **Effect_Catalog**: The persistent store (JSON manifest + Python modules) that holds all registered animation effect definitions, their metadata, parameter schemas, and thumbnail references.
- **Effect_Skeleton**: A parameterized Manim scene template that defines the animation structure, accepted parameters, default styles, and preview configuration for a single reusable effect.
- **Effect_Registry**: The runtime component that discovers, loads, and indexes Effect_Skeletons from the Effect_Catalog, replacing the current hardcoded dispatch dictionary in `manim_codegen.py`.
- **Effect_Browser**: The frontend UI component that displays available effects from the Effect_Catalog with previews, parameter descriptions, and category filters.
- **Codegen_Engine**: The backend component that takes an Effect_Skeleton and user-supplied parameters to produce a complete, renderable Manim Python file.
- **Scene_Instruction**: The JSON object describing what to render for a given scene, including the effect type, data payload, and style overrides.
- **Effect_Category**: A grouping label for effects (e.g., "charts", "text", "social", "data", "editorial") used for browsing and filtering.
- **Reference_Video**: A short rendered sample video (MP4) for each Effect_Skeleton that demonstrates the effect in action with its preview configuration parameters, stored alongside the catalog assets.
- **PDF_Forensic_Effect**: An Effect_Skeleton that converts PDF report pages (annual reports, earnings, SEC filings) to images and uses Manim to animate highlight regions, camera zooms, and sequential reveals on the source document, replacing generic stock footage with actual institutional source material.
- **Forensic_Zoom_Effect**: An Effect_Skeleton that enhances timeseries charts with a camera dive into a specific event date, blurring the surrounding context and highlighting the target price action with a golden glow rectangle.
- **Volatility_Shadow_Effect**: An Effect_Skeleton that overlays a semi-transparent red area fill on timeseries charts during drawdown periods, visualizing the distance between the running all-time high and the current price as a "Pain Zone".
- **Relative_Velocity_Effect**: An Effect_Skeleton for multi-line timeseries that renders a dynamic vertical arrow between two series with a real-time updating percentage spread label, visualizing the performance gap as lines diverge.
- **Contextual_Heatmap_Effect**: An Effect_Skeleton that overlays a green-to-red background color gradient on timeseries charts based on a benchmark index's performance, providing macroeconomic context for stock price movements.
- **Bull_Bear_Projection_Effect**: An Effect_Skeleton that extends a timeseries chart from "Today" into three projected future paths (Optimistic, Realistic, Pessimistic) using configurable growth rates, visualizing risk-adjusted expectations.
- **Moat_Radar_Effect**: An Effect_Skeleton that renders a spider/radar chart comparing two companies across multiple configurable metrics, with overlapping semi-transparent polygons and animated progressive reveal.
- **Atomic_Reveal_Effect**: An Effect_Skeleton that displays a central entity and animates component parts flying out radially in an exploded-view layout, with sentiment color-coding and highlight emphasis on the key driver or risk factor.
- **Sync_Points**: A list of timestamp-keyed anchors within an Effect_Skeleton that align specific animation moments (e.g., a price drop highlight, an event marker reveal) to narration audio timestamps provided by the SynthesizerService, ensuring visual beats land precisely when the narrator references them.
- **Quality_Profile**: A named render configuration (e.g., "draft", "production") within an Effect_Skeleton that specifies resolution, frame rate, sampling quality, and encoder settings, allowing fast preview renders during editing and high-fidelity final renders for publishing.
- **Legacy_Mapper**: An alias table within the EffectRegistry that maps deprecated or ambiguous scene type strings (e.g., "data_chart") to the correct Effect_Skeleton identifier (e.g., "timeseries", "bar_chart", "donut") based on sub-type hints in the Scene_Instruction, ensuring backward compatibility without requiring script rewrites.
- **Scene_Expansion**: A pacing mechanism in the orchestrator that detects high-impact data scenes shorter than a minimum duration threshold and force-extends the visual duration by appending breathing room after the narration ends, preventing rushed visual delivery.
- **Initial_Wait**: A configurable delay parameter in the Manim codegen that holds the chart in a steady-state baseline view before executing the primary animation action, giving the viewer time to orient before the data event fires.
- **Forensic_SlowMo**: A rendering strategy for the Forensic_Zoom_Effect that replaces slow camera travel with an instant jump-cut into the focus window, reclaiming visual attention time for the actual data point rather than spending it on transit.
- **SSML_Data_Pause**: An SSML `<break>` tag injected after high-impact data phrases (e.g., percentage drops, revenue figures) in the synthesized narration, creating a natural audio pause that gives the visual engine additional seconds to animate the corresponding data point.
- **Static_Freeze**: A 2-second hold appended to the end of a Manim render when the scene contains a data delta exceeding 10% delivered in under 3 seconds of narration, ensuring the viewer has time to visually retain the key data point before the next scene cuts in.
- **Narrative_Category**: An Effect_Category grouping for effects that direct viewer attention to specific moments or eras in the data story — overlays, zone colorings, and shockwave markers that layer on top of structural chart effects.
- **Motion_Category**: An Effect_Category grouping for effects that control camera behavior, playback speed, and dynamic visual properties like glow intensity — the "motion language" layer that governs how the viewer experiences time and emphasis.
- **Liquidity_Shock_Effect**: An Effect_Skeleton that renders a shockwave pulse on a timeseries chart at a specified event date, combining a vertical flash line, ripple shockwave ring, camera micro-shake, and brief price-line glow to viscerally convey crashes, rate hikes, or black swan events.
- **Momentum_Glow_Effect**: An Effect_Skeleton that dynamically adjusts the glow intensity and color of a timeseries line based on its slope/acceleration over a rolling window, making high-momentum periods visually "hot" with a neon trail and cooling periods fade back to a neutral baseline.
- **Regime_Shift_Effect**: An Effect_Skeleton that renders labeled, color-coded background zones on a timeseries chart to delineate economic eras (e.g., QE Era, Rate Hikes), providing temporal context for price movements without cluttering the data line itself.
- **Speed_Ramp_Effect**: An Effect_Skeleton that varies the playback speed of a timeseries line-draw animation across configurable time segments, allowing boring decades to fast-forward and critical crash periods to play in slow motion.
- **Capital_Flow_Effect**: An Effect_Skeleton that renders animated directional arrows between labeled entities (assets, sectors, geographies) with arrow thickness proportional to flow amount, visualizing money movement between components of a financial system.
- **Compounding_Explosion_Effect**: An Effect_Skeleton that animates an exponential growth curve with a dramatic glow breakpoint where the curve steepens beyond a threshold, visually conveying the moment compounding "kicks in" with a pulse and intensified line glow.
- **Market_Share_Territory_Effect**: An Effect_Skeleton that renders area fills between competing timeseries lines, coloring the territory each series "owns" above or below the other, visualizing market share or performance dominance shifts over time.
- **Historical_Rank_Effect**: An Effect_Skeleton that renders a vertical percentile ladder showing where a current value sits within its historical distribution, with labeled percentile bands and an animated marker that settles into position.

## Requirements

### Requirement 1: Effect Skeleton Definition

**User Story:** As a video producer, I want each animation effect to be defined as a self-contained, parameterized skeleton, so that I can reuse the same visual pattern across multiple videos with different data.

#### Acceptance Criteria

1. THE Effect_Skeleton SHALL define a unique string identifier, a human-readable display name, an Effect_Category (one of CHARTS, TEXT, SOCIAL, DATA, EDITORIAL, NARRATIVE, or MOTION), and a description.
2. THE Effect_Skeleton SHALL declare a parameter schema specifying the accepted data fields, their types, default values, and whether each field is required or optional.
3. THE Effect_Skeleton SHALL contain a Manim scene template that produces a complete renderable Python file when combined with parameter values.
4. THE Effect_Skeleton SHALL declare a preview configuration specifying a set of sample parameter values sufficient to render a thumbnail preview.
5. THE Effect_Skeleton SHALL include a Reference_Video file path pointing to a rendered MP4 sample that demonstrates the effect using the preview configuration parameters.
6. WHEN an Effect_Skeleton is instantiated with parameter values that satisfy the declared schema, THE Codegen_Engine SHALL produce a valid Manim Python file.
7. IF an Effect_Skeleton is instantiated with parameter values that violate the declared schema, THEN THE Codegen_Engine SHALL return a descriptive validation error identifying the invalid fields.

### Requirement 2: Effect Catalog Persistence

**User Story:** As a video producer, I want all registered effects to be persisted in a catalog, so that effects survive restarts and can be versioned alongside the codebase.

#### Acceptance Criteria

1. THE Effect_Catalog SHALL store effect metadata (identifier, display name, category, description, parameter schema, preview config, reference video path) in a JSON manifest file.
2. THE Effect_Catalog SHALL store each Effect_Skeleton's Manim template as a separate Python module file alongside the manifest.
3. THE Effect_Catalog SHALL store each Effect_Skeleton's Reference_Video as an MP4 file in a designated assets directory alongside the manifest.
4. WHEN the application starts, THE Effect_Registry SHALL load all Effect_Skeletons from the Effect_Catalog and index them by identifier.
5. WHEN a new Effect_Skeleton is added to the Effect_Catalog, THE Effect_Registry SHALL make the new effect available without requiring an application restart beyond a catalog reload.
6. THE Effect_Catalog SHALL include all existing scene types (text_overlay, bar_chart, line_chart, pie_chart, code_snippet, reddit_post, stat_callout, quote_block, section_title, bullet_reveal, comparison, fullscreen_statement, data_chart, timeseries, horizontal_bar, grouped_bar, donut) as pre-registered Effect_Skeletons.

### Requirement 3: Effect Registry and Dispatch

**User Story:** As a developer, I want a single registry that resolves effect identifiers to their skeletons, so that the rendering pipeline uses a unified lookup instead of a hardcoded dictionary.

#### Acceptance Criteria

1. THE Effect_Registry SHALL replace the hardcoded generator dictionary in the Codegen_Engine with a dynamic lookup against the Effect_Catalog.
2. WHEN a Scene_Instruction references a registered effect identifier, THE Effect_Registry SHALL return the corresponding Effect_Skeleton.
3. IF a Scene_Instruction references an unregistered effect identifier, THEN THE Effect_Registry SHALL raise an error listing all available effect identifiers.
4. THE Effect_Registry SHALL provide a list_effects operation that returns all registered effect identifiers with their display names, categories, and descriptions.
5. THE Effect_Registry SHALL support filtering the effect list by Effect_Category.

### Requirement 4: Codegen Engine Integration

**User Story:** As a developer, I want the codegen engine to use Effect_Skeletons for code generation, so that adding new effects does not require modifying the core codegen dispatch logic.

#### Acceptance Criteria

1. WHEN the Codegen_Engine receives a Scene_Instruction, THE Codegen_Engine SHALL resolve the effect identifier through the Effect_Registry, validate parameters against the skeleton's schema, and produce a Manim Python file.
2. THE Codegen_Engine SHALL preserve backward compatibility with existing Scene_Instruction formats so that previously authored video scripts render without modification.
3. WHEN an Effect_Skeleton includes style overrides in the Scene_Instruction, THE Codegen_Engine SHALL merge the overrides with the skeleton's default styles, with overrides taking precedence.
4. THE Codegen_Engine SHALL support Yahoo Finance data enrichment for data-chart category effects, consistent with the current _enrich_from_yahoo behavior.

### Requirement 5: Effect Browser API

**User Story:** As a frontend developer, I want API endpoints to browse and query the effect library, so that the UI can display available effects to the user.

#### Acceptance Criteria

1. THE Studio_API SHALL expose a GET endpoint that returns all registered effects with their identifiers, display names, categories, descriptions, and parameter schemas.
2. THE Studio_API SHALL expose a GET endpoint that returns effects filtered by a specified Effect_Category.
3. THE Studio_API SHALL expose a GET endpoint that returns the full detail of a single effect by identifier, including the parameter schema and preview configuration.
4. WHEN the Effect_Catalog contains zero effects for a requested category, THE Studio_API SHALL return an empty list with a 200 status code.

### Requirement 6: Effect Browser UI

**User Story:** As a video producer, I want to browse available animation effects in the UI, so that I can discover and select the right visual for each scene.

#### Acceptance Criteria

1. THE Effect_Browser SHALL display a grid of available effects showing each effect's display name, category badge, description, and an inline Reference_Video preview.
2. WHEN a user hovers over or clicks an effect card in the Effect_Browser, THE Effect_Browser SHALL play the Reference_Video for that effect.
3. THE Effect_Browser SHALL allow filtering effects by Effect_Category using a category selector.
4. WHEN a user selects an effect from the Effect_Browser, THE Effect_Browser SHALL display the effect's parameter schema with field names, types, and default values.
5. WHEN a user selects an effect and provides parameter values, THE Effect_Browser SHALL allow applying that effect to the currently selected scene in the visual panel.
6. THE Effect_Browser SHALL be accessible from the existing Visual Panel as a side panel or modal.

### Requirement 7: Effect Extraction from Existing Videos

**User Story:** As a video producer, I want to save a custom effect created for a specific video as a reusable skeleton in the library, so that the library grows organically from real production work.

#### Acceptance Criteria

1. WHEN a rendered scene uses parameter values and style overrides that differ from the base Effect_Skeleton defaults, THE Studio_API SHALL expose an endpoint to save the customized configuration as a new Effect_Skeleton in the Effect_Catalog.
2. THE save-as-effect operation SHALL require the user to provide a unique identifier, display name, category, and description for the new effect.
3. IF the provided identifier conflicts with an existing effect in the Effect_Catalog, THEN THE Studio_API SHALL return a conflict error without overwriting the existing effect.
4. WHEN a new effect is saved, THE Effect_Registry SHALL make the new effect available for immediate use without application restart.

### Requirement 8: Effect Skeleton Serialization Round-Trip

**User Story:** As a developer, I want to ensure that effect skeletons can be serialized to the catalog format and deserialized back without data loss, so that the catalog remains a reliable source of truth.

#### Acceptance Criteria

1. THE Effect_Catalog SHALL serialize Effect_Skeleton metadata to JSON and deserialize JSON back to Effect_Skeleton metadata.
2. FOR ALL valid Effect_Skeleton objects, serializing to JSON then deserializing back SHALL produce an equivalent Effect_Skeleton object (round-trip property).
3. THE Effect_Catalog SHALL pretty-print Effect_Skeleton metadata to human-readable JSON format.
4. IF the Effect_Catalog encounters malformed JSON during deserialization, THEN THE Effect_Catalog SHALL return a descriptive parse error identifying the location of the malformation.

### Requirement 9: PDF Forensic Effect

**User Story:** As a video producer, I want to animate highlights on actual company PDF reports (annual reports, earnings, SEC filings), so that I can replace generic stock footage with credible source documents that build institutional trust.

#### Acceptance Criteria

1. WHEN a PDF file path and page number are provided, THE PDF_Forensic_Effect SHALL convert the specified page to a high-resolution image suitable for 1080p video rendering.
2. THE PDF_Forensic_Effect SHALL accept highlight region specifications as bounding box coordinates (x, y, width, height) or as a text search string that resolves to bounding box coordinates on the page.
3. WHEN a highlight region is specified, THE PDF_Forensic_Effect SHALL generate a Manim scene that displays the PDF page image, animates a highlight rectangle or underline over the specified region, and zooms the camera into the highlighted area using MovingCameraScene.
4. WHEN multiple highlight regions are specified for a single page, THE PDF_Forensic_Effect SHALL animate the highlights in sequential order, zooming to each region in turn.
5. THE PDF_Forensic_Effect SHALL support configurable highlight styles including rectangle overlay, underline, and margin annotation, with color and opacity parameters.
6. THE PDF_Forensic_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "pdf_forensic", category "editorial", and a parameter schema covering PDF path, page number, highlight regions, and highlight style.
7. IF the specified PDF file path is invalid or the page number is out of range, THEN THE PDF_Forensic_Effect SHALL return a descriptive error identifying the invalid input.
8. IF a text search string does not match any content on the specified page, THEN THE PDF_Forensic_Effect SHALL return a descriptive error indicating the text was not found.
9. THE PDF_Forensic_Effect SHALL include a Reference_Video demonstrating a sample highlight animation on a placeholder PDF page using the preview configuration parameters.

### Requirement 10: Forensic Zoom Effect

**User Story:** As a video producer, I want the camera to dive into a specific event date on a timeseries chart, blurring the surrounding context and highlighting the target price action, so that I can create a temporal anchor that focuses the viewer's attention on a critical moment.

#### Acceptance Criteria

1. WHEN a full-range timeseries chart is displayed, THE Forensic_Zoom_Effect SHALL animate the camera from the wide view into a narrow window centered on the specified focus_date parameter using MovingCameraScene.
2. THE Forensic_Zoom_Effect SHALL accept parameters for focus_date (target date to zoom into), focus_window_days (default 30), glow_color (default gold), and blur_opacity (opacity level for fading the non-focus area).
3. WHEN the camera reaches the focus window, THE Forensic_Zoom_Effect SHALL apply a fade effect to the chart regions outside the focus window, reducing their opacity to the specified blur_opacity value.
4. WHEN the focus window is isolated, THE Forensic_Zoom_Effect SHALL render a SurroundingRectangle with the specified glow_color around the price action within the focus window.
5. THE Forensic_Zoom_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "forensic_zoom", category "data", and a parameter schema covering focus_date, focus_window_days, glow_color, and blur_opacity.
6. IF the specified focus_date falls outside the range of the timeseries data, THEN THE Forensic_Zoom_Effect SHALL return a descriptive error identifying the out-of-range date and the valid date range.
7. THE Forensic_Zoom_Effect SHALL include a Reference_Video demonstrating a camera dive into a sample event date on a placeholder timeseries using the preview configuration parameters.

### Requirement 11: Volatility Shadow Effect

**User Story:** As a video producer, I want to visualize drawdown periods on a timeseries chart as a faint red shadow between the running all-time high and the current price, so that viewers can immediately see the "Pain Zone" where investors experienced losses from the peak.

#### Acceptance Criteria

1. WHILE the timeseries line is drawing and the current price is below the running maximum of all prices drawn so far, THE Volatility_Shadow_Effect SHALL render a semi-transparent area fill between the running all-time-high line and the actual price line.
2. THE Volatility_Shadow_Effect SHALL accept parameters for shadow_color (default "#FF453A"), shadow_opacity (default 0.2), and show_drawdown_pct (whether to display a drawdown percentage label).
3. THE Volatility_Shadow_Effect SHALL dynamically grow and shrink the shadow area as the timeseries line animates, adding shadow geometry only during drawdown periods and removing the shadow when the price recovers to a new all-time high.
4. WHEN show_drawdown_pct is enabled, THE Volatility_Shadow_Effect SHALL display a percentage label indicating the current drawdown from the running all-time high, updating the label as the line draws.
5. THE Volatility_Shadow_Effect SHALL use a Polygon or area fill colored with the specified shadow_color at the specified shadow_opacity to represent the Pain Zone.
6. THE Volatility_Shadow_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "volatility_shadow", category "data", and a parameter schema covering shadow_color, shadow_opacity, and show_drawdown_pct.
7. IF the timeseries data contains fewer than two data points, THEN THE Volatility_Shadow_Effect SHALL return a descriptive error indicating insufficient data for drawdown calculation.
8. THE Volatility_Shadow_Effect SHALL include a Reference_Video demonstrating the shadow overlay on a placeholder timeseries with at least one drawdown period using the preview configuration parameters.

### Requirement 12: Relative Velocity Comparison Effect

**User Story:** As a video producer, I want to visualize the performance gap between two timeseries as a dynamic arrow with a real-time percentage spread label, so that viewers can see not just two lines but the divergence story between them.

#### Acceptance Criteria

1. WHEN two timeseries lines are animating simultaneously, THE Relative_Velocity_Effect SHALL render a dynamic vertical arrow between the two series at the rightmost drawn data point.
2. THE Relative_Velocity_Effect SHALL accept parameters for series_a_name, series_b_name, show_delta_arrow (default true), delta_format (e.g., "+{:.0f}% Lead"), and arrow_color.
3. WHILE the two timeseries lines are drawing, THE Relative_Velocity_Effect SHALL update the vertical arrow position and the percentage spread label continuously to track the rightmost drawn point.
4. THE Relative_Velocity_Effect SHALL use a DecimalNumber component to display the percentage spread, updating the value in real-time as the lines animate.
5. WHEN show_delta_arrow is enabled, THE Relative_Velocity_Effect SHALL render the arrow pointing from the lower series to the higher series, with the percentage label formatted according to the delta_format parameter.
6. THE Relative_Velocity_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "relative_velocity", category "data", and a parameter schema covering series_a_name, series_b_name, show_delta_arrow, delta_format, and arrow_color.
7. IF the two timeseries have mismatched date ranges, THEN THE Relative_Velocity_Effect SHALL align the comparison to the overlapping date range and return a warning identifying the non-overlapping periods.
8. THE Relative_Velocity_Effect SHALL include a Reference_Video demonstrating the dynamic arrow and spread label on two placeholder timeseries using the preview configuration parameters.

### Requirement 13: Contextual Heatmap Effect

**User Story:** As a video producer, I want to overlay a background color gradient on timeseries charts that shifts from green to red based on a benchmark index's performance, so that viewers can immediately see the macroeconomic context behind a stock's price movement without asking "Why did this happen?"

#### Acceptance Criteria

1. WHEN a benchmark_ticker parameter is provided, THE Contextual_Heatmap_Effect SHALL fetch the benchmark's historical price data via Yahoo Finance enrichment consistent with the existing _enrich_from_yahoo behavior.
2. THE Contextual_Heatmap_Effect SHALL render a background color gradient layer behind the primary stock's price line, where the color at each x-position reflects the benchmark's performance at that point in time.
3. WHILE the benchmark value at a given x-position is above its starting value, THE Contextual_Heatmap_Effect SHALL shade the background at that position using the specified green_color parameter.
4. WHILE the benchmark value at a given x-position is below its starting value, THE Contextual_Heatmap_Effect SHALL shade the background at that position using the specified red_color parameter.
5. THE Contextual_Heatmap_Effect SHALL accept parameters for benchmark_ticker (e.g., "^GSPC" for S&P 500), green_color, red_color, heatmap_opacity, and benchmark_label.
6. THE Contextual_Heatmap_Effect SHALL render the heatmap layer at the specified heatmap_opacity so that the primary price line remains clearly visible above the gradient.
7. THE Contextual_Heatmap_Effect SHALL display the benchmark_label text on the chart to identify which benchmark is driving the background color.
8. THE Contextual_Heatmap_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "contextual_heatmap", category "data", and a parameter schema covering benchmark_ticker, green_color, red_color, heatmap_opacity, and benchmark_label.
9. IF the benchmark_ticker fails to resolve via Yahoo Finance enrichment, THEN THE Contextual_Heatmap_Effect SHALL return a descriptive error identifying the invalid ticker symbol.
10. THE Contextual_Heatmap_Effect SHALL include a Reference_Video demonstrating the green-to-red background gradient on a placeholder timeseries with a sample benchmark using the preview configuration parameters.

### Requirement 14: Bull vs Bear Multi-Path Projection Effect

**User Story:** As a video producer, I want to project three possible future price paths (Optimistic, Realistic, Pessimistic) from the current price on a timeseries chart, so that viewers can see risk-adjusted expectations and the compounding difference between bull and bear scenarios.

#### Acceptance Criteria

1. THE Bull_Bear_Projection_Effect SHALL draw the actual historical price line normally up to the most recent data point, labeled as "Today".
2. WHEN the historical price line reaches "Today", THE Bull_Bear_Projection_Effect SHALL animate three dashed projection lines fanning out from the last known price point into the future.
3. THE Bull_Bear_Projection_Effect SHALL calculate each projection path from the last known price using the specified annual growth rate compounded over the projection_years parameter (default 3).
4. THE Bull_Bear_Projection_Effect SHALL render the Optimistic path as a green dashed line, the Realistic path as a blue or white dashed line, and the Pessimistic path as a red dashed line.
5. THE Bull_Bear_Projection_Effect SHALL accept parameters for optimistic_rate (e.g., 0.25 for 25% annual growth), realistic_rate (e.g., 0.10), pessimistic_rate (e.g., -0.15), projection_years (default 3), and projection_labels (e.g., ["Bull", "Base", "Bear"]).
6. THE Bull_Bear_Projection_Effect SHALL display a label at the end of each projected line showing the projection_label text and the projected price value.
7. THE Bull_Bear_Projection_Effect SHALL animate the fan-out smoothly, with each projection line growing outward from the "Today" point.
8. THE Bull_Bear_Projection_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "bull_bear_projection", category "data", and a parameter schema covering optimistic_rate, realistic_rate, pessimistic_rate, projection_years, and projection_labels.
9. IF the timeseries data contains fewer than two data points, THEN THE Bull_Bear_Projection_Effect SHALL return a descriptive error indicating insufficient data for projection calculation.
10. THE Bull_Bear_Projection_Effect SHALL include a Reference_Video demonstrating the three-path fan-out on a placeholder timeseries using the preview configuration parameters.

### Requirement 15: Moat Comparison Radar Effect

**User Story:** As a video producer, I want to compare two companies on multiple qualitative and quantitative metrics using a spider/radar chart, so that viewers can see the competitive moat analysis beyond just stock price.

#### Acceptance Criteria

1. THE Moat_Radar_Effect SHALL render a spider/radar chart with N axes (default 5) arranged radially, each axis labeled with the corresponding metric from the metric_labels parameter.
2. THE Moat_Radar_Effect SHALL accept parameters for company_a_name, company_a_values (list of floats 0-100), company_b_name, company_b_values (list of floats 0-100), metric_labels (list of strings), company_a_color, and company_b_color.
3. THE Moat_Radar_Effect SHALL render two overlapping polygons on the radar chart, one per company, each filled with the specified color at partial opacity so both polygons remain visible.
4. THE Moat_Radar_Effect SHALL animate the chart in sequence: axes and metric labels appear first, then the Company A polygon grows from the center outward, then the Company B polygon grows from the center outward.
5. WHEN both polygons are fully rendered, THE Moat_Radar_Effect SHALL use Indicate on the metric axis where Company A has the largest advantage over Company B.
6. THE Moat_Radar_Effect SHALL display a legend showing both company names with their corresponding colors.
7. THE Moat_Radar_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "moat_radar", category "data", and a parameter schema covering company_a_name, company_a_values, company_b_name, company_b_values, metric_labels, company_a_color, and company_b_color.
8. IF the lengths of company_a_values, company_b_values, and metric_labels are not equal, THEN THE Moat_Radar_Effect SHALL return a descriptive error identifying the mismatched list lengths.
9. IF any value in company_a_values or company_b_values falls outside the 0-100 range, THEN THE Moat_Radar_Effect SHALL return a descriptive error identifying the out-of-range value.
10. THE Moat_Radar_Effect SHALL include a Reference_Video demonstrating the two-company radar comparison on placeholder metrics using the preview configuration parameters.

### Requirement 16: Atomic Component Reveal Effect

**User Story:** As a video producer, I want to display a central entity and animate its component parts flying out radially in an exploded-view layout, so that viewers can see the breakdown of a complex company or system into its constituent drivers and risks.

#### Acceptance Criteria

1. THE Atomic_Reveal_Effect SHALL display a central labeled block representing the entity_name parameter.
2. THE Atomic_Reveal_Effect SHALL accept parameters for entity_name (central label), components (list of objects each containing name, value, and sentiment with values "positive", "negative", or "neutral"), highlight_component (name of the component to emphasize), and layout ("radial" or "grid").
3. WHEN the animation begins, THE Atomic_Reveal_Effect SHALL animate the component blocks outward from the central entity using LaggedStart, positioning them according to the specified layout parameter.
4. THE Atomic_Reveal_Effect SHALL color-code each component block based on its sentiment value: green for "positive", red for "negative", and a neutral color for "neutral".
5. WHEN all components have been revealed, THE Atomic_Reveal_Effect SHALL apply Indicate to the component matching the highlight_component parameter, creating a pulsing or glowing emphasis.
6. WHEN the highlight animation completes, THE Atomic_Reveal_Effect SHALL fade in value labels on each component block displaying the component's value field.
7. WHERE the layout parameter is set to "radial", THE Atomic_Reveal_Effect SHALL position components in an evenly-spaced circular arrangement around the central entity.
8. WHERE the layout parameter is set to "grid", THE Atomic_Reveal_Effect SHALL position components in a structured grid arrangement around the central entity.
9. THE Atomic_Reveal_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "atomic_reveal", category "editorial", and a parameter schema covering entity_name, components, highlight_component, and layout.
10. IF the highlight_component parameter does not match any component name in the components list, THEN THE Atomic_Reveal_Effect SHALL return a descriptive error identifying the unmatched highlight component name.
11. THE Atomic_Reveal_Effect SHALL include a Reference_Video demonstrating the radial exploded-view animation on a placeholder entity with sample components using the preview configuration parameters.

### Requirement 17: Narration-Sync Anchors

**User Story:** As a video producer, I want animation highlights and visual beats to land precisely when the narrator references them, so that the "calm" rhythm of the video is preserved and the viewer never sees a visual event disconnected from the audio.

#### Acceptance Criteria

1. THE Effect_Skeleton SHALL declare an optional sync_points field: a list of named anchors (e.g., "drop_highlight", "event_marker_reveal") that identify moments in the animation where timing alignment with narration is critical.
2. THE CodegenEngine SHALL accept an optional list of audio timestamps (in seconds) from the SynthesizerService, one per declared sync_point, and inject Manim `self.wait()` calls into the generated code to align each sync_point with its corresponding audio timestamp.
3. WHEN sync_points are declared but no audio timestamps are provided, THE CodegenEngine SHALL generate the animation using default timing (evenly spaced across the target duration) so that the effect remains renderable without audio.
4. WHEN the number of provided audio timestamps does not match the number of declared sync_points, THE CodegenEngine SHALL return a descriptive error identifying the mismatch (expected N sync_points, received M timestamps).
5. THE sync_points field SHALL be included in the Effect_Skeleton's parameter schema and serialized/deserialized as part of the Effect_Catalog manifest.
6. THE Effect_Browser UI SHALL display the declared sync_point names for each effect so that the producer can see which moments are alignable.

### Requirement 18: Hardware-Aware Render Profiles

**User Story:** As a video producer working on an M4 48GB machine, I want to render fast draft previews during editing and high-fidelity production renders for publishing, so that I don't waste time waiting for full-quality renders while iterating on the visual design.

#### Acceptance Criteria

1. THE Effect_Skeleton SHALL declare a quality_profiles field containing at least two named profiles: "draft" and "production".
2. THE "draft" quality profile SHALL specify reduced resolution (720p), lower frame rate (15fps), and low-sampling Manim quality flags suitable for fast preview rendering.
3. THE "production" quality profile SHALL specify full resolution (1080p or 4K), 30fps frame rate, high-bitrate encoding, and high-sampling Manim quality flags suitable for final publishing.
4. WHEN the CodegenEngine receives a render request, THE CodegenEngine SHALL accept an optional quality_profile parameter (default "production") and apply the corresponding profile's resolution, frame rate, and quality settings to the generated Manim command.
5. THE Reference_Video for each Effect_Skeleton SHALL be rendered using the "draft" quality profile to minimize catalog build time and storage.
6. THE render API endpoint SHALL accept an optional quality_profile query parameter, passing it through to the CodegenEngine.
7. THE Effect_Browser UI SHALL display the available quality profiles for each effect and allow the producer to select a profile before triggering a render.
8. IF a render request specifies a quality_profile name that does not exist in the Effect_Skeleton's quality_profiles, THEN THE CodegenEngine SHALL return a descriptive error listing the available profile names.

### Requirement 19: Legacy Type Mapping

**User Story:** As a developer, I want deprecated or ambiguous scene type strings from existing video scripts to automatically resolve to the correct Effect_Skeleton, so that backward compatibility is bulletproof and no existing scripts break when the library is deployed.

#### Acceptance Criteria

1. THE EffectRegistry SHALL maintain a LegacyMapper: an alias table that maps deprecated scene type strings to Effect_Skeleton identifiers.
2. THE LegacyMapper SHALL map the "data_chart" type string to the appropriate sub-type skeleton (e.g., "timeseries", "bar_chart", "donut", "horizontal_bar", "grouped_bar") by inspecting the chart_type field in the Scene_Instruction's data payload.
3. WHEN the EffectRegistry receives a resolve request for a type string that exists in the LegacyMapper, THE EffectRegistry SHALL transparently redirect to the mapped Effect_Skeleton identifier without requiring the caller to know about the mapping.
4. THE LegacyMapper SHALL be configurable via a JSON mapping file (legacy_mappings.json) stored alongside the Effect_Catalog manifest, so that new aliases can be added without code changes.
5. WHEN a legacy type string is resolved through the LegacyMapper, THE EffectRegistry SHALL log a deprecation warning identifying the legacy string and the resolved skeleton identifier.
6. IF a legacy type string maps to a sub-type resolution (like "data_chart") and the required sub-type hint field is missing from the Scene_Instruction, THEN THE EffectRegistry SHALL fall back to a configured default skeleton for that legacy type and log a warning.
7. THE LegacyMapper SHALL be included in the list_effects output as a separate "aliases" section so that the Effect_Browser can display which legacy names map to which effects.

### Requirement 20: Scene Expansion for High-Impact Data Beats

**User Story:** As a video producer, I want scenes containing high-impact data visuals (data_chart, forensic_zoom) to automatically receive extra visual breathing room when the narration is short, so that the viewer can process the data point before the next scene cuts in.

#### Acceptance Criteria

1. WHEN a scene's narration duration is shorter than 6 seconds AND the scene's visual instruction type is "data_chart", "forensic_zoom", "volatility_shadow", or "bull_bear_projection", THE orchestrator SHALL force-extend the visual duration by appending a configurable padding (default 2.5 seconds) after the narration ends.
2. THE Scene_Expansion padding duration SHALL be configurable via an environment variable (SCENE_EXPANSION_PAD_S, default 2.5) and overridable per-scene via a style_override field "expansion_pad_s".
3. WHEN Scene_Expansion is applied, THE orchestrator SHALL log the original narration duration, the expansion amount, and the final visual duration for debugging.
4. THE Scene_Expansion logic SHALL NOT apply when the scene's narration duration is 6 seconds or longer, as the visual already has sufficient breathing room.
5. THE Scene_Expansion logic SHALL be implemented in the visual_service or orchestrator layer, not in the Manim codegen, so that the Manim template simply receives a longer target_duration.

### Requirement 21: Pre-Drawing Initial Wait (Baseline Establishment)

**User Story:** As a video producer, I want data chart animations to hold a steady-state baseline view before executing the primary data action, so that the viewer can orient themselves to the chart context before the dramatic event fires.

#### Acceptance Criteria

1. THE Effect_Skeleton SHALL declare an optional initial_wait parameter (in seconds, default 0) that specifies how long the chart holds in its baseline state before the primary animation action begins.
2. WHEN initial_wait is greater than 0, THE CodegenEngine SHALL generate Manim code that displays the chart axes, labels, and any pre-event data line for the specified duration before triggering the primary animation (e.g., the price drop, the bar growth).
3. FOR data_chart and timeseries effects, THE default initial_wait SHALL be 1.5 seconds, establishing a "Snap" pacing pattern: 0–1.5s baseline hold, 1.5–3.0s rapid action, 3.0s–end indicator hold.
4. THE initial_wait parameter SHALL be included in the Effect_Skeleton's parameter schema and overridable via style_overrides in the Scene_Instruction.
5. WHEN initial_wait is 0, THE CodegenEngine SHALL generate code that begins the primary animation immediately (backward-compatible with current behavior).

### Requirement 22: Forensic Slow-Mo (Jump-Cut Zoom)

**User Story:** As a video producer, I want the Forensic Zoom effect to use an instant jump-cut into the focus window instead of a slow camera travel, so that visual attention time is spent on the actual data point rather than wasted on transit animation.

#### Acceptance Criteria

1. THE Forensic_Zoom_Effect SHALL support a zoom_mode parameter with values "travel" (smooth camera pan) and "jump_cut" (instant transition), defaulting to "jump_cut".
2. WHEN zoom_mode is "jump_cut", THE Forensic_Zoom_Effect SHALL display the wide chart for a configurable wide_hold duration (default 1.0 seconds), then instantly transition the camera to the focus window without intermediate animation frames.
3. WHEN zoom_mode is "travel", THE Forensic_Zoom_Effect SHALL animate the camera smoothly from the wide view to the focus window (original behavior).
4. THE jump_cut transition SHALL reclaim at least 1.5 seconds of visual time compared to the travel mode, allowing the focus window to be displayed for longer.
5. THE zoom_mode and wide_hold parameters SHALL be included in the Forensic_Zoom_Effect's parameter schema and registered in the Effect_Catalog.

### Requirement 23: SSML Data Pause Injection

**User Story:** As a video producer, I want the narration synthesis to automatically insert audio pauses after high-impact data phrases (percentage changes, revenue figures), so that the render pipeline sees a longer audio duration for that scene and the Manim animation has the extra seconds it needs to breathe.

#### Acceptance Criteria

1. THE SSML builder (or equivalent narration preprocessing layer) SHALL detect high-impact data phrases in the narration text, defined as: percentage values with absolute magnitude ≥ 10% (e.g., "16 percent drop", "-23%"), and currency values ≥ $1B (e.g., "$28 billion").
2. WHEN a high-impact data phrase is detected, THE SSML builder SHALL insert a `<break time="1s"/>` tag (or equivalent pause mechanism) immediately after the phrase in the synthesized audio.
3. THE pause duration SHALL be configurable via a DATA_PAUSE_MS environment variable (default 1000ms) and overridable per-scene via a style_override field "data_pause_ms".
4. THE inserted pause SHALL increase the total audio duration for the scene, which the render pipeline uses as the target_duration for the Manim render, automatically giving the visual more time without manual intervention.
5. THE SSML Data Pause logic SHALL NOT insert pauses when the scene's narration duration already exceeds 8 seconds, to avoid making long scenes unnecessarily longer.
6. THE SSML builder SHALL log each detected high-impact phrase and the pause duration inserted for debugging and tuning.

### Requirement 24: Static Freeze for High-Delta Data Points

**User Story:** As a video producer following the "Calm Capitalist" brand standard, I want the visual engine to append a 2-second static freeze to the end of any scene where a data delta exceeds 10% and the narration delivers it in under 3 seconds, so that the viewer has time to visually retain the key data point before the next scene cuts in.

#### Acceptance Criteria

1. WHEN a Scene_Instruction contains a data delta (percentage change) with absolute magnitude ≥ 10% AND the narration duration for that scene is under 3 seconds, THE CodegenEngine SHALL append a 2-second Static_Freeze to the end of the generated Manim render.
2. THE Static_Freeze SHALL hold the final frame of the animation (including any glow, indicator, or value badge) completely still for the freeze duration.
3. THE freeze duration SHALL be configurable via a STATIC_FREEZE_S environment variable (default 2.0) and overridable per-scene via a style_override field "freeze_duration_s".
4. THE CodegenEngine SHALL detect the data delta by inspecting the Scene_Instruction's data payload for fields indicating percentage change (e.g., events with delta values, chart annotations with percentage labels).
5. THE Static_Freeze SHALL be applied after all other animation effects (including sync_point waits and initial_wait) have completed.
6. WHEN the Static_Freeze is applied, THE CodegenEngine SHALL log the detected delta, the narration duration, and the freeze duration for debugging.
7. THE Static_Freeze SHALL NOT be applied when the narration duration is 3 seconds or longer, as the visual already has sufficient pacing.


### Requirement 25: Liquidity Shock Effect

**User Story:** As a video producer, I want to render a visceral shockwave pulse on a timeseries chart at a specific event date (crash, rate hike, black swan), so that the viewer physically feels the impact of the event rather than just seeing a line drop.

#### Acceptance Criteria

1. WHEN a shock_date parameter is provided, THE Liquidity_Shock_Effect SHALL render a vertical flash line at the corresponding x-position on the timeseries chart, fading from full opacity to transparent over 0.5 seconds.
2. THE Liquidity_Shock_Effect SHALL animate a circular ripple shockwave ring expanding outward from the shock_date position on the price line, using the specified shock_color parameter (default "#FF453A").
3. WHEN the shockwave fires, THE Liquidity_Shock_Effect SHALL apply a camera micro-shake to the MovingCameraScene frame, displacing the camera by a configurable pixel offset proportional to the shock_intensity parameter (float 0.0–1.0, default 0.7) for 0.3 seconds.
4. WHEN the shockwave fires, THE Liquidity_Shock_Effect SHALL briefly glow the price line segment within a 5-day window around the shock_date using the shock_color at elevated opacity for 0.4 seconds before fading back to the normal line color.
5. THE Liquidity_Shock_Effect SHALL accept parameters for shock_date (ISO date string), shock_color (default "#FF453A"), shock_intensity (float 0.0–1.0, default 0.7), and shock_label (text displayed near the flash line, e.g., "Lehman Collapse").
6. WHEN shock_label is provided, THE Liquidity_Shock_Effect SHALL render the label text above the flash line, fading in after the shockwave animation completes.
7. THE Liquidity_Shock_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "liquidity_shock", category "narrative", and a parameter schema covering shock_date, shock_color, shock_intensity, and shock_label.
8. IF the shock_date falls outside the range of the timeseries data, THEN THE Liquidity_Shock_Effect SHALL return a descriptive error identifying the out-of-range date and the valid date range.
9. IF shock_intensity is outside the 0.0–1.0 range, THEN THE Liquidity_Shock_Effect SHALL return a descriptive error identifying the invalid intensity value.
10. THE Liquidity_Shock_Effect SHALL include a Reference_Video demonstrating the shockwave pulse on a placeholder timeseries at a sample crash date using the preview configuration parameters.

### Requirement 26: Momentum Glow Effect

**User Story:** As a video producer, I want the timeseries line to dynamically glow based on its slope and acceleration, so that high-momentum rallies and sell-offs are visually "hot" and cooling periods fade to neutral — letting the viewer feel the energy of the market without needing explicit annotations.

#### Acceptance Criteria

1. WHILE the timeseries line is drawing, THE Momentum_Glow_Effect SHALL compute a rolling slope over the specified momentum_window parameter (integer number of data points, default 20) at each drawn point.
2. WHEN the absolute rolling slope exceeds a configurable glow_threshold (default: 1 standard deviation above the mean slope), THE Momentum_Glow_Effect SHALL render the line segment with an outer glow trail using the specified glow_color parameter (default "#00FFAA" for upward momentum, "#FF453A" for downward momentum).
3. THE Momentum_Glow_Effect SHALL scale the glow_intensity (float 0.0–1.0, default 0.8) proportionally to the magnitude of the rolling slope, so that stronger momentum produces a more intense glow.
4. WHEN the rolling slope falls below the glow_threshold, THE Momentum_Glow_Effect SHALL fade the glow trail back to the baseline line color over 0.3 seconds of animation time.
5. THE Momentum_Glow_Effect SHALL accept parameters for momentum_window (default 20), glow_color_up (default "#00FFAA"), glow_color_down (default "#FF453A"), glow_intensity (default 0.8), and glow_threshold_sigma (default 1.0).
6. THE Momentum_Glow_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "momentum_glow", category "motion", and a parameter schema covering momentum_window, glow_color_up, glow_color_down, glow_intensity, and glow_threshold_sigma.
7. IF the timeseries data contains fewer data points than the momentum_window parameter, THEN THE Momentum_Glow_Effect SHALL return a descriptive error indicating insufficient data for momentum calculation.
8. THE Momentum_Glow_Effect SHALL include a Reference_Video demonstrating dynamic glow transitions on a placeholder timeseries with at least one high-momentum period using the preview configuration parameters.

### Requirement 27: Regime Shift Effect

**User Story:** As a video producer, I want to color-code background zones on a timeseries chart by economic era (e.g., QE Era 2008–2015, Rate Hikes 2022–2024), so that the viewer immediately understands the macro context behind price movements without the narrator having to explain every regime change.

#### Acceptance Criteria

1. THE Regime_Shift_Effect SHALL accept a regimes parameter: a list of objects each containing start (ISO date string), end (ISO date string), label (display text), and color (hex color string).
2. FOR EACH regime in the regimes list, THE Regime_Shift_Effect SHALL render a vertical background zone spanning the full chart height from the regime's start date to its end date, filled with the specified color at a configurable zone_opacity parameter (default 0.15).
3. THE Regime_Shift_Effect SHALL render each regime's label text at the top of the corresponding zone, positioned to avoid overlapping the price line.
4. THE Regime_Shift_Effect SHALL animate the zones appearing sequentially from left to right using FadeIn, so that each era is revealed as the timeseries line draws through it.
5. THE Regime_Shift_Effect SHALL render the zones behind the price line layer so that the data remains clearly visible above the colored backgrounds.
6. THE Regime_Shift_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "regime_shift", category "narrative", and a parameter schema covering regimes and zone_opacity.
7. IF any regime's start date is after its end date, THEN THE Regime_Shift_Effect SHALL return a descriptive error identifying the invalid regime entry.
8. IF any regime's date range falls entirely outside the timeseries data range, THEN THE Regime_Shift_Effect SHALL return a descriptive error identifying the out-of-range regime.
9. THE Regime_Shift_Effect SHALL include a Reference_Video demonstrating labeled background zones on a placeholder timeseries spanning multiple eras using the preview configuration parameters.

### Requirement 28: Speed Ramp Effect

**User Story:** As a video producer, I want to vary the playback speed of a timeseries line-draw animation across different time segments, so that boring decades fast-forward and critical crash periods play in slow motion — giving the viewer a cinematic sense of time compression and expansion.

#### Acceptance Criteria

1. THE Speed_Ramp_Effect SHALL accept a speed_regimes parameter: a list of objects each containing start (ISO date string), end (ISO date string), and speed (float multiplier where 1.0 is normal speed, >1.0 is fast-forward, <1.0 is slow motion).
2. WHILE the timeseries line is drawing through a segment covered by a speed_regime, THE Speed_Ramp_Effect SHALL adjust the animation rate so that the line draws at the specified speed multiplier relative to the base drawing rate.
3. THE Speed_Ramp_Effect SHALL smoothly interpolate between adjacent speed regimes over a configurable transition_frames parameter (default 10 frames) to avoid jarring speed changes.
4. WHEN a speed_regime has speed > 2.0, THE Speed_Ramp_Effect SHALL render a subtle fast-forward visual indicator (e.g., faint ">>" overlay) during the accelerated segment.
5. WHEN a speed_regime has speed < 0.5, THE Speed_Ramp_Effect SHALL render a subtle slow-motion visual indicator (e.g., faint "◀◀" overlay) during the decelerated segment.
6. THE Speed_Ramp_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "speed_ramp", category "motion", and a parameter schema covering speed_regimes and transition_frames.
7. IF any speed_regime's speed value is ≤ 0, THEN THE Speed_Ramp_Effect SHALL return a descriptive error identifying the invalid speed value.
8. IF any speed_regime's start date is after its end date, THEN THE Speed_Ramp_Effect SHALL return a descriptive error identifying the invalid regime entry.
9. THE Speed_Ramp_Effect SHALL include a Reference_Video demonstrating speed variation on a placeholder timeseries with at least one fast-forward and one slow-motion segment using the preview configuration parameters.

### Requirement 29: Capital Flow Effect

**User Story:** As a video producer, I want to animate directional arrows showing money flowing between assets, sectors, or geographies, so that the viewer can see capital rotation as a dynamic process rather than a static table of numbers.

#### Acceptance Criteria

1. THE Capital_Flow_Effect SHALL accept a flows parameter: a list of objects each containing from_entity (string label), to_entity (string label), flow_amount (numeric value), and optional flow_color (hex color string).
2. THE Capital_Flow_Effect SHALL render labeled node blocks for each unique entity referenced in the flows list, positioned in a configurable layout parameter ("horizontal", "circular", or "custom" with explicit x,y coordinates).
3. FOR EACH flow in the flows list, THE Capital_Flow_Effect SHALL animate a directional arrow from the from_entity node to the to_entity node, with arrow thickness proportional to the flow_amount relative to the maximum flow in the list.
4. THE Capital_Flow_Effect SHALL animate the arrows sequentially using LaggedStart, with each arrow growing from source to destination accompanied by a flow_amount label that fades in at the arrow midpoint.
5. THE Capital_Flow_Effect SHALL accept parameters for layout (default "horizontal"), arrow_base_width (default 2), flow_label_format (default "${:.1f}B"), and animation_duration (default 4.0 seconds).
6. THE Capital_Flow_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "capital_flow", category "narrative", and a parameter schema covering flows, layout, arrow_base_width, flow_label_format, and animation_duration.
7. IF the flows list is empty, THEN THE Capital_Flow_Effect SHALL return a descriptive error indicating that at least one flow is required.
8. IF a from_entity or to_entity references an entity not present in any other flow (isolated node with only outbound or only inbound), THE Capital_Flow_Effect SHALL still render that entity as a node — this is valid (source-only or sink-only nodes are expected).
9. THE Capital_Flow_Effect SHALL include a Reference_Video demonstrating animated capital flows between three placeholder entities using the preview configuration parameters.

### Requirement 30: Compounding Explosion Effect

**User Story:** As a video producer, I want to animate an exponential growth curve that dramatically glows and pulses at the breakpoint where compounding "kicks in", so that the viewer viscerally understands the hockey-stick moment rather than just seeing a smooth curve.

#### Acceptance Criteria

1. THE Compounding_Explosion_Effect SHALL accept parameters for principal (starting value), rate (annual growth rate as decimal, e.g., 0.10 for 10%), years (integer, total duration), and breakpoint_year (optional, the year at which the glow pulse fires; defaults to the year where the second derivative of the curve exceeds a threshold).
2. THE Compounding_Explosion_Effect SHALL animate the exponential curve drawing from year 0 to the specified years parameter, computing each point as principal × (1 + rate)^year.
3. WHEN the curve reaches the breakpoint_year, THE Compounding_Explosion_Effect SHALL fire a glow pulse on the line: the line segment from breakpoint_year onward SHALL render with an intensified glow using a configurable explosion_color parameter (default "#FFD700") at elevated opacity for 0.5 seconds before settling to a sustained but dimmer glow.
4. THE Compounding_Explosion_Effect SHALL render value labels at the start point, breakpoint, and end point of the curve showing the compounded value at each milestone.
5. THE Compounding_Explosion_Effect SHALL accept additional parameters for explosion_color (default "#FFD700"), line_color (default "#FFFFFF"), and show_doubling_markers (boolean, default true — renders faint horizontal lines at each doubling of the principal).
6. THE Compounding_Explosion_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "compounding_explosion", category "narrative", and a parameter schema covering principal, rate, years, breakpoint_year, explosion_color, line_color, and show_doubling_markers.
7. IF rate is 0 or negative, THEN THE Compounding_Explosion_Effect SHALL return a descriptive error indicating that compounding requires a positive growth rate.
8. IF years is less than 2, THEN THE Compounding_Explosion_Effect SHALL return a descriptive error indicating insufficient duration for compounding visualization.
9. THE Compounding_Explosion_Effect SHALL include a Reference_Video demonstrating the hockey-stick glow breakpoint on a placeholder growth curve using the preview configuration parameters.

### Requirement 31: Market Share Territory Effect

**User Story:** As a video producer, I want to fill the area between competing timeseries lines with color to show which company or asset "owns" the territory at each point in time, so that market share shifts and performance dominance are immediately visible as colored regions rather than abstract line crossings.

#### Acceptance Criteria

1. THE Market_Share_Territory_Effect SHALL accept a series parameter: a list of objects each containing name (string label), data (list of {date, value} points), and territory_color (hex color string).
2. WHEN two series are provided, THE Market_Share_Territory_Effect SHALL render an area fill between the two lines, colored with the territory_color of whichever series is on top at each x-position.
3. WHEN more than two series are provided, THE Market_Share_Territory_Effect SHALL render stacked area fills between adjacent series (sorted by value at each x-position), each colored with the corresponding series' territory_color.
4. THE Market_Share_Territory_Effect SHALL accept a fill_opacity parameter (default 0.3) controlling the transparency of the territory fills so that the underlying lines remain visible.
5. WHEN a territory ownership change occurs (one series crosses above another), THE Market_Share_Territory_Effect SHALL animate a brief color transition at the crossover point over 0.2 seconds of animation time.
6. THE Market_Share_Territory_Effect SHALL render a legend showing each series name with its corresponding territory_color.
7. THE Market_Share_Territory_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "market_share_territory", category "data", and a parameter schema covering series, fill_opacity, and territory_colors.
8. IF the series list contains fewer than two series, THEN THE Market_Share_Territory_Effect SHALL return a descriptive error indicating that at least two series are required for territory comparison.
9. IF any two series have non-overlapping date ranges, THEN THE Market_Share_Territory_Effect SHALL return a descriptive error identifying the series with mismatched date ranges.
10. THE Market_Share_Territory_Effect SHALL include a Reference_Video demonstrating territory fills between two placeholder series with at least one crossover point using the preview configuration parameters.

### Requirement 32: Historical Rank Effect

**User Story:** As a video producer, I want to show where a current value sits within its historical distribution as a vertical percentile ladder, so that the viewer instantly understands whether a metric is historically cheap, expensive, normal, or extreme without needing to interpret a full timeseries.

#### Acceptance Criteria

1. THE Historical_Rank_Effect SHALL accept parameters for current_value (numeric), historical_values (list of numeric values representing the historical distribution), metric_label (display text, e.g., "P/E Ratio"), and percentile_bands (optional list of labeled thresholds, default: [{"label": "Cheap", "pct": 25}, {"label": "Normal", "pct": 50}, {"label": "Expensive", "pct": 75}, {"label": "Extreme", "pct": 95}]).
2. THE Historical_Rank_Effect SHALL compute the percentile rank of current_value within the historical_values distribution.
3. THE Historical_Rank_Effect SHALL render a vertical ladder visualization with labeled horizontal bands at each percentile_band threshold, colored from green (low percentile) through yellow (mid) to red (high percentile).
4. THE Historical_Rank_Effect SHALL animate a marker settling into the computed percentile position on the ladder, using a drop-and-bounce easing animation.
5. WHEN the marker settles, THE Historical_Rank_Effect SHALL display a label showing the metric_label, the current_value, and the computed percentile rank (e.g., "P/E Ratio: 28.5 — 82nd percentile").
6. THE Historical_Rank_Effect SHALL be registered in the Effect_Catalog as a standard Effect_Skeleton with identifier "historical_rank", category "data", and a parameter schema covering current_value, historical_values, metric_label, and percentile_bands.
7. IF historical_values contains fewer than 10 data points, THEN THE Historical_Rank_Effect SHALL return a descriptive error indicating insufficient historical data for meaningful percentile calculation.
8. THE Historical_Rank_Effect SHALL include a Reference_Video demonstrating the percentile ladder with a placeholder metric value settling into position using the preview configuration parameters.