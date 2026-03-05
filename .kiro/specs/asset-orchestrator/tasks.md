# Implementation Plan: Asset Orchestrator

## Overview

Build the `asset_orchestrator` Python module that transforms visual instructions from video scripts into production-ready 1080p/30fps MP4 video assets. Implementation proceeds bottom-up: exceptions → config/models → registry → mapper → chart templates → code snippet/text overlay scenes → renderer → FFmpeg wrapper → orchestrator → logger integration, with tests woven in alongside each component.

## Tasks

- [x] 1. Set up project structure, dependencies, and exception hierarchy
  - [x] 1.1 Create the `asset_orchestrator/` package directory with `__init__.py`
    - Create `asset_orchestrator/__init__.py` exporting the public API
    - _Requirements: N/A (project scaffolding)_

  - [x] 1.2 Create the exception hierarchy in `asset_orchestrator/exceptions.py`
    - Implement `AssetOrchestratorError` base exception
    - Implement `ValidationError(missing_fields: list[str])` with message listing missing fields
    - Implement `UnknownSceneTypeError(invalid_type: str, valid_types: list[str])` with descriptive message
    - Implement `DuplicateSceneTypeError(type_key: str)`
    - Implement `RenderError(error_output: str, instruction: dict)` storing both attributes
    - Implement `CompositionError(error_output: str, command: str)`
    - Implement `ParseError(position: int, message: str)` with position in message
    - _Requirements: 1.3, 1.5, 2.4, 4.3, 7.4, 8.2_

  - [x] 1.3 Create data models and config in `asset_orchestrator/config.py`
    - Implement `VisualInstruction` dataclass with fields: `type`, `title`, `data`, `style` (optional)
    - Implement `RenderConfig` dataclass with defaults: 1920×1080, 30fps, `output/renders`, mp4
    - Implement `CompositionConfig` dataclass with defaults: libx264, aac, 5M video bitrate, 192k audio bitrate, `output/composed`
    - Implement `BatchResult` dataclass with `total`, `succeeded`, `failed`, `results`
    - _Requirements: 3.6, 4.1, 5.9, 6.1, 6.2, 8.3_

  - [x] 1.4 Add `manim` dependency to `requirements.txt` if not already present
    - Ensure `manim`, `hypothesis`, and `pytest` are listed
    - _Requirements: N/A (dependency management)_

- [x] 2. Implement Scene Registry
  - [x] 2.1 Create `asset_orchestrator/scene_registry.py`
    - Implement `SceneRegistry` class with internal `dict[str, type]` mapping
    - Implement `get(type_key)` → returns Scene class or raises `UnknownSceneTypeError`
    - Implement `register(type_key, scene_class)` → raises `DuplicateSceneTypeError` on collision
    - Implement `list_types()` → returns all registered keys
    - Initialize with built-in types in `__init__`: `bar_chart`, `line_chart`, `pie_chart`, `code_snippet`, `text_overlay` (use placeholder classes initially, wire real classes later)
    - _Requirements: 1.4, 2.1, 2.3, 2.4_

  - [ ]* 2.2 Write property tests for Scene Registry (`tests/property/test_props_registry.py`)
    - **Property 4: Registry maps types to class references** — for any registered type key, `get()` returns a class that is a subclass of Manim's Scene
    - **Property 6: Runtime registration round-trip** — after `register(key, cls)`, `get(key)` returns `cls`
    - **Property 7: Duplicate registration raises error** — registering an existing key raises `DuplicateSceneTypeError`
    - **Validates: Requirements 2.1, 2.3, 2.4**

  - [ ]* 2.3 Write unit tests for Scene Registry (`tests/unit/test_scene_registry.py`)
    - Test all 5 built-in types are registered at init
    - Test `get()` with valid and invalid keys
    - Test `register()` with new key and duplicate key
    - Test `list_types()` returns expected keys
    - _Requirements: 1.4, 2.1, 2.3, 2.4_

- [x] 3. Implement Scene Mapper
  - [x] 3.1 Create `asset_orchestrator/scene_mapper.py`
    - Implement `SceneMapper.__init__(registry: SceneRegistry)`
    - Implement `map(instruction: dict)` → validates required fields (`type`, `title`, `data`), looks up type in registry, instantiates Scene with `title`, `data`, `style`
    - Raise `ValidationError` with missing field names when fields are absent
    - Raise `UnknownSceneTypeError` when type not in registry
    - Implement `serialize(instruction: dict) -> str` using `json.dumps`
    - Implement `deserialize(json_str: str) -> dict` using `json.loads`, raising `ParseError` with position on failure
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 2.2, 2.5, 7.1, 7.2, 7.3, 7.4_

  - [ ]* 3.2 Write property tests for Scene Mapper validation (`tests/property/test_props_validation.py`)
    - **Property 1: Valid instruction acceptance** — any dict with `type` (registered), `title`, `data` is accepted without exception
    - **Property 2: Type validation matches registry membership** — `UnknownSceneTypeError` raised iff type not in registry
    - **Property 3: Missing fields reported in ValidationError** — missing required fields listed in error message
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5**

  - [ ]* 3.3 Write property tests for serialization (`tests/property/test_props_serialization.py`)
    - **Property 18: Visual_Instruction JSON round-trip** — serialize then deserialize produces equivalent dict
    - **Property 19: Invalid JSON raises ParseError with position** — malformed JSON raises `ParseError` with character position
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Chart Templates
  - [x] 5.1 Create `asset_orchestrator/chart_templates.py` with `BarChartScene`
    - Subclass Manim `Scene`
    - Accept `title`, `data` (labels + values), `style` in constructor
    - Implement `construct()`: dark gray background, white text, labeled axes, data bars with values above each bar, accent colors
    - Truncate title > 60 chars with ellipsis
    - Group categories into "Other" when > 10
    - _Requirements: 3.1, 3.4, 3.5, 3.7_

  - [x] 5.2 Add `LineChartScene` to `asset_orchestrator/chart_templates.py`
    - Subclass Manim `Scene`
    - Implement `construct()`: dark gray background, white text, labeled axes, data points with connecting lines, title
    - Apply same truncation and grouping rules
    - _Requirements: 3.2, 3.4, 3.5, 3.7_

  - [x] 5.3 Add `PieChartScene` to `asset_orchestrator/chart_templates.py`
    - Subclass Manim `Scene`
    - Implement `construct()`: dark gray background, white text, labeled segments with percentage values, title
    - Apply same truncation and grouping rules
    - _Requirements: 3.3, 3.4, 3.5, 3.7_

  - [ ]* 5.4 Write property tests for chart data transforms (`tests/property/test_props_charts.py`)
    - **Property 8: Category grouping into "Other" for large datasets** — >10 categories produces ≤11 segments, "Other" value equals sum of grouped
    - **Property 9: Title truncation at 60 characters** — titles >60 chars truncated with "...", ≤60 unchanged
    - **Validates: Requirements 3.4, 3.7**

  - [ ]* 5.5 Write unit tests for chart templates (`tests/unit/test_chart_templates.py`)
    - Test BarChartScene construction with sample data
    - Test LineChartScene construction with sample data
    - Test PieChartScene construction with sample data
    - Test exactly 10 categories (no grouping) and 11 categories (grouping triggered)
    - Test title of exactly 60 chars (no truncation) and 61 chars (truncation)
    - Test dark background color scheme is applied
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7_

- [x] 6. Implement Code Snippet and Text Overlay Scenes
  - [x] 6.1 Create `asset_orchestrator/code_snippet_scene.py`
    - Subclass Manim `Scene`
    - Accept `title`, `data` (containing code string and language), `style`
    - Implement `construct()`: render syntax-highlighted code block with dark background consistent with chart templates
    - _Requirements: 1.4, 3.5_

  - [x] 6.2 Create `asset_orchestrator/text_overlay_scene.py`
    - Subclass Manim `Scene`
    - Accept `title`, `data` (containing text content), `style` (font size, position, animation)
    - Implement `construct()`: render text overlay with dark background consistent with chart templates
    - _Requirements: 1.4, 3.5_

  - [x] 6.3 Wire all scene classes into Scene Registry
    - Update `SceneRegistry.__init__` to register `BarChartScene`, `LineChartScene`, `PieChartScene`, `CodeSnippetScene`, `TextOverlayScene` as the built-in types
    - _Requirements: 1.4, 2.1_

- [x] 7. Implement Renderer
  - [x] 7.1 Create `asset_orchestrator/renderer.py`
    - Implement `Renderer.__init__(config: RenderConfig)`
    - Implement `render(scene, instruction)` → invoke Manim to render scene to MP4, apply config (1080p, 30fps), derive filename from instruction type + sanitized title, return absolute path
    - Implement `sanitize_filename(title: str) -> str` as static method — replace non-alphanumeric chars with underscores
    - Raise `RenderError` on Manim failure with error output and instruction
    - Clean up temp files on failure
    - _Requirements: 3.6, 3.8, 4.1, 4.2, 4.3, 4.4, 4.5, 8.4_

  - [ ]* 7.2 Write property tests for rendering (`tests/property/test_props_rendering.py`)
    - **Property 10: Render output is 1080p at 30fps** — render config passed to Manim specifies 1920×1080 and 30fps
    - **Property 11: Filename derived from type and sanitized title** — output filename contains type and sanitized title, resides in configured output dir
    - **Property 12: Filename sanitization replaces non-alphanumeric characters** — result contains only alnum + underscores, and is idempotent
    - **Property 13: RenderError contains error output and instruction** — raised error stores both attributes
    - **Property 14: All output paths are absolute** — returned paths start with `/`
    - **Validates: Requirements 3.6, 3.8, 4.1, 4.2, 4.3, 4.4, 4.5**

  - [ ]* 7.3 Write unit tests for Renderer (`tests/unit/test_renderer.py`)
    - Test `sanitize_filename` with various inputs (spaces, special chars, already clean)
    - Test render success returns absolute path in configured output dir
    - Test render failure raises `RenderError` with correct attributes
    - Test temp file cleanup on failure
    - Mock `subprocess.run` for Manim calls
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 8.4_

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement FFmpeg Wrapper
  - [x] 9.1 Create `asset_orchestrator/ffmpeg_wrapper.py`
    - Implement `FFmpegWrapper.__init__(config: CompositionConfig | None)` — check FFmpeg on PATH via `shutil.which`, raise `EnvironmentError` if missing, apply default config if None
    - Implement `compose(audio_path, video_path, output_path)` → validate file existence, build FFmpeg command (H.264 + AAC, configurable bitrates), loop video if audio longer, trim video if audio shorter, preserve 1080p/30fps, create output dir if missing, return absolute path
    - Raise `FileNotFoundError` for missing audio/video files
    - Raise `CompositionError` on FFmpeg failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4_

  - [ ]* 9.2 Write property tests for FFmpeg Wrapper (`tests/property/test_props_ffmpeg.py`)
    - **Property 15: Missing input files raise FileNotFoundError** — non-existent audio/video path raises `FileNotFoundError` with path in message
    - **Property 16: FFmpeg command reflects CompositionConfig** — custom config values appear in constructed command
    - **Property 17: Output directory created if missing** — parent directory created before writing
    - **Validates: Requirements 5.5, 5.6, 5.9, 6.1, 6.4**

  - [ ]* 9.3 Write unit tests for FFmpeg Wrapper (`tests/unit/test_ffmpeg_wrapper.py`)
    - Test default config values (H.264, AAC, 5M, 192k)
    - Test `EnvironmentError` when FFmpeg not on PATH (mock `shutil.which`)
    - Test `FileNotFoundError` for missing audio and video files
    - Test compose success returns absolute path
    - Test output directory creation
    - Mock `subprocess.run` for FFmpeg calls
    - _Requirements: 5.1, 5.5, 5.6, 5.7, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4_

- [x] 10. Implement Asset Orchestrator (batch processing)
  - [x] 10.1 Create `asset_orchestrator/orchestrator.py`
    - Implement `AssetOrchestrator.__init__(render_config, composition_config, log_level)` — instantiate `SceneRegistry`, `SceneMapper`, `Renderer`, `FFmpegWrapper`, configure logger
    - Implement `process_instruction(instruction, audio_path)` → map instruction to scene, render to MP4, optionally compose with audio, return result dict (`status`, `output_path` or `error` + `instruction`)
    - Implement `process_batch(instructions, audio_paths)` → iterate instructions, continue on per-item failure, collect results, return `BatchResult` with `total`, `succeeded`, `failed`, `results`
    - Log each instruction received (type + title), render start/complete with elapsed ms, errors at ERROR level with full context
    - Clean up temp files on render failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 10.2 Write property tests for batch processing (`tests/property/test_props_batch.py`)
    - **Property 20: Batch continues on per-item failure** — batch of N instructions with K invalid still processes all N, result has N entries
    - **Property 21: Batch summary invariant** — `total == succeeded + failed == len(results)`
    - **Property 22: Temp file cleanup on render failure** — temp files removed after failed render
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]* 10.3 Write unit tests for Asset Orchestrator (`tests/unit/test_orchestrator.py`)
    - Test `process_instruction` success path
    - Test `process_instruction` with invalid instruction (continues without crash)
    - Test `process_batch` with mixed success/failure
    - Test batch with 0 instructions
    - Test batch where all fail
    - Test batch where all succeed
    - Test error logging includes instruction context
    - Mock Manim and FFmpeg subprocess calls
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 11. Implement Logger
  - [x] 11.1 Create `asset_orchestrator/logger.py`
    - Implement `get_logger(name, level)` factory function
    - Support configurable log levels: DEBUG, INFO, WARNING, ERROR
    - Format log entries with timestamp, level, module name, and message
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 11.2 Integrate logger into all components
    - Add logging calls in `SceneMapper` (instruction received), `Renderer` (render start/complete with elapsed ms), `FFmpegWrapper` (log command before execution), `AssetOrchestrator` (errors with full context and stack trace)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 11.3 Write property tests for logging (`tests/property/test_props_logging.py`)
    - **Property 23: Logging includes instruction type, title, and render timing** — log output contains type, title, and elapsed ms
    - **Property 24: FFmpeg commands logged before execution** — log contains full FFmpeg command string
    - **Property 25: Errors logged at ERROR level with full context** — ERROR entry with stack trace, instruction, and error details
    - **Property 26: Configurable log levels** — only entries at or above configured level are emitted
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 12. Package initialization and wiring
  - [x] 12.1 Update `asset_orchestrator/__init__.py` with public API exports
    - Export `AssetOrchestrator`, `SceneMapper`, `SceneRegistry`, `Renderer`, `FFmpegWrapper`
    - Export `RenderConfig`, `CompositionConfig`, `VisualInstruction`, `BatchResult`
    - Export all custom exceptions
    - _Requirements: N/A (package API)_

  - [x] 12.2 Create `tests/conftest.py` shared fixtures for asset orchestrator tests (if not already covered)
    - Add fixtures for sample `VisualInstruction` dicts, mock Manim subprocess, mock FFmpeg subprocess, temporary output directories
    - _Requirements: N/A (test infrastructure)_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All Manim and FFmpeg subprocess calls should be mocked in tests to avoid external dependencies
