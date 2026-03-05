# Requirements Document

## Introduction

The Stock Footage Visuals module extends the Asset Orchestrator to produce real YouTube-quality video scenes by combining stock video footage from Pexels with programmatic text overlays via FFmpeg. Currently, the Asset Orchestrator renders all visuals through Manim — which works well for data charts and code snippets but cannot produce the "real visuals" needed for engaging YouTube content (B-roll of people, cities, nature, technology, etc.). This module adds a `PexelsClient` for fetching relevant stock footage by keyword, an `FFmpegCompositor` for overlaying text/stats on video backgrounds, and new scene types (`stock_video`, `stock_with_text`, `stock_with_stat`, `stock_quote`) that the existing orchestrator can process alongside Manim scenes. Manim remains available for data-specific scenes (charts, code) but is no longer the primary visual engine.

## Glossary

- **Pexels_API**: Free stock video/photo API (pexels.com) providing HD/4K footage with no watermarks under the Pexels license
- **PexelsClient**: Python client that searches and downloads stock video clips from Pexels by keyword
- **FFmpegCompositor**: Component that overlays text, statistics, and graphics on top of stock video backgrounds using FFmpeg drawtext and overlay filters
- **Stock_Scene**: A scene type that uses stock footage as the visual background instead of Manim-generated animation
- **B-Roll**: Background video footage that plays while narration is heard — the visual backbone of YouTube videos
- **Ken_Burns_Effect**: Slow pan/zoom on a still image to create motion from a static photo
- **Text_Overlay**: Text rendered on top of video footage using FFmpeg drawtext filters (distinct from Manim's TextOverlayScene)
- **Scene_Keyword_Extractor**: Logic that derives search keywords from scene narration text and title to find relevant stock footage

## Requirements

### Requirement 1: Pexels API Integration

**User Story:** As a pipeline operator, I want to search and download stock video clips from Pexels by keyword, so that scenes have real visual backgrounds instead of only Manim animations.

#### Acceptance Criteria

1. THE PexelsClient SHALL accept a Pexels API key from the environment variable `PEXELS_API_KEY`
2. THE PexelsClient SHALL search for videos by keyword query and return a list of video results with metadata (id, url, duration, width, height, video_files)
3. THE PexelsClient SHALL download a video file to a specified local path and return the absolute file path
4. THE PexelsClient SHALL prefer HD (1920x1080) or higher resolution video files when multiple qualities are available
5. THE PexelsClient SHALL cache downloaded videos locally to avoid re-downloading the same clip
6. IF the Pexels API key is missing or invalid, THEN THE PexelsClient SHALL raise a `ConfigurationError` with a descriptive message
7. IF the Pexels API returns no results for a query, THEN THE PexelsClient SHALL return an empty list without raising an exception
8. THE PexelsClient SHALL respect Pexels API rate limits (200 requests/hour) using the existing rate limiter pattern
9. THE PexelsClient SHALL support a `min_duration` parameter (default 5 seconds) to filter out clips that are too short for scene backgrounds

### Requirement 2: Scene Keyword Extraction

**User Story:** As a pipeline operator, I want relevant search keywords automatically derived from scene narration and title, so that stock footage matches the scene content.

#### Acceptance Criteria

1. THE keyword extractor SHALL accept a scene's narration_text and title and return a list of search keywords
2. THE keyword extractor SHALL extract the most relevant 2-4 keywords that describe the visual content needed
3. THE keyword extractor SHALL use GPT-4o-mini to intelligently extract visual keywords from narration text (e.g., "people filing taxes" from a narration about tax withholding)
4. THE keyword extractor SHALL fall back to simple noun extraction (without LLM) if the OpenAI API call fails
5. THE keyword extractor SHALL cache keyword results to avoid redundant LLM calls for the same narration text

### Requirement 3: FFmpeg Text/Stat Overlay Compositor

**User Story:** As a content producer, I want text, statistics, and quotes overlaid on stock footage backgrounds, so that key information is visually communicated alongside real video.

#### Acceptance Criteria

1. THE FFmpegCompositor SHALL overlay title text on a stock video background at a configurable position (top, center, bottom)
2. THE FFmpegCompositor SHALL overlay a large statistic value with a label below it (e.g., "$10,000" with "UNEXPECTED TAX BILL") centered on the video
3. THE FFmpegCompositor SHALL overlay a styled quote block with attribution text on the video
4. THE FFmpegCompositor SHALL apply a semi-transparent dark overlay (configurable opacity, default 0.5) behind text to ensure readability
5. THE FFmpegCompositor SHALL use a clean sans-serif font (configurable, default: system sans-serif) with configurable font size
6. THE FFmpegCompositor SHALL trim or loop the stock video to match a target duration (derived from narration audio length or a default of 8 seconds)
7. THE FFmpegCompositor SHALL output composed scenes at 1080p (1920x1080) and 30fps as MP4 (H.264 + AAC)
8. THE FFmpegCompositor SHALL support a fade-in (0.5s) and fade-out (0.5s) on each composed scene

### Requirement 4: Stock Footage Scene Types

**User Story:** As a pipeline operator, I want new scene types that use stock footage backgrounds, so that the video script JSON can specify real-visual scenes alongside Manim data scenes.

#### Acceptance Criteria

1. THE system SHALL support a `stock_video` scene type: stock footage background with optional title text overlay
2. THE system SHALL support a `stock_with_text` scene type: stock footage with a heading and body text overlay
3. THE system SHALL support a `stock_with_stat` scene type: stock footage with a large stat value and label overlay
4. THE system SHALL support a `stock_quote` scene type: stock footage with a styled quote and attribution overlay
5. ALL stock scene types SHALL accept a `keywords` field in their data dict for Pexels search (if omitted, keywords are auto-extracted from narration)
6. ALL stock scene types SHALL be registered in the existing SceneRegistry alongside Manim scene types
7. THE orchestrator SHALL detect stock scene types and route them through the PexelsClient + FFmpegCompositor pipeline instead of the Manim renderer

### Requirement 5: Orchestrator Integration

**User Story:** As a pipeline operator, I want the existing Asset Orchestrator to seamlessly handle both Manim and stock footage scenes in the same batch, so that a single video can mix data visualizations with real footage.

#### Acceptance Criteria

1. THE AssetOrchestrator SHALL detect whether an instruction is a stock scene type or a Manim scene type and route accordingly
2. THE AssetOrchestrator SHALL process stock scenes by: extracting keywords → searching Pexels → downloading footage → compositing text overlay → returning the composed MP4 path
3. THE AssetOrchestrator SHALL fall back to a solid-color background with text overlay if Pexels returns no results for a scene's keywords
4. THE existing batch processing, error handling, and logging behavior SHALL apply equally to stock footage scenes
5. THE AssetOrchestrator SHALL support mixing stock and Manim scenes in the same batch without any configuration changes

### Requirement 6: Video Script JSON Extension

**User Story:** As a content producer, I want the video script JSON format to support stock footage scene types, so that scripts can specify real-visual scenes.

#### Acceptance Criteria

1. THE video script JSON SHALL accept `stock_video`, `stock_with_text`, `stock_with_stat`, and `stock_quote` as valid visual_instruction types
2. THE `stock_with_text` type SHALL accept data fields: `heading`, `body`, and optional `keywords`
3. THE `stock_with_stat` type SHALL accept data fields: `value`, `label`, `subtitle`, and optional `keywords`
4. THE `stock_quote` type SHALL accept data fields: `quote`, `attribution`, and optional `keywords`
5. THE `stock_video` type SHALL accept data fields: `title` (optional) and `keywords` (optional)
