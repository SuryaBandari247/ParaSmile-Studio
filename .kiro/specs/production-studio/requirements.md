# Requirements Document

## Introduction

The Video Production Studio replaces the current Streamlit-based Pipeline UI with a modern React frontend and FastAPI backend, providing a full-featured project-based workflow for the Faceless Technical Media Engine. Instead of a single-session linear pipeline, the studio introduces persistent projects with UUID-based identity, stage-based navigation (RESEARCH → TOPIC → SCRIPT → AUDIO → VISUAL → RENDER), and granular control over every production step — from individual API source triggers and script versioning to SRT-based audio timelines and single-scene visual re-renders. The backend exposes a REST API with WebSocket support for real-time job status, while the frontend delivers a responsive SPA with inline editing, drag-and-drop reordering, and live preview capabilities. All data is persisted in SQLite with versioned artifacts, enabling iterative refinement without data loss.

## Glossary

- **Project**: A persistent video production unit identified by a UUID, tracking status and current stage through the full pipeline
- **Project_Status**: The lifecycle state of a project: DRAFT, IN_PROGRESS, REVIEW, RENDERED, PUBLISHED
- **Pipeline_Stage**: The current production step: RESEARCH, TOPIC, SCRIPT, AUDIO, VISUAL, RENDER
- **Topic**: A candidate video subject with a unique ID (TOPIC-001 pattern), metadata, and selection status
- **Script_Version**: A numbered revision of a video script associated with a topic, stored as VideoScript JSON
- **Audio_Segment**: A single narration unit within an SRT timeline, with timing, text, voice parameters, and audio file
- **Scene**: A visual composition unit with type, data, stock footage, rendered output, and thumbnail
- **Job**: A background task (research, synthesis, render) tracked with status and input/output payloads
- **Artifact**: A versioned file produced by the pipeline (script JSON, audio MP3, rendered MP4, thumbnail PNG)
- **SRT_Timeline**: An ordered sequence of Audio_Segments using SubRip Timing format (HH:MM:SS,mmm)
- **Visual_Type**: The category of visual instruction for a scene (manim_animation, stock_footage, text_overlay, chart, screen_recording)
- **Voice_Params**: Per-segment voice configuration mapped to SSML attributes (speed, pitch, emphasis)

## Requirements

### Requirement 1: Project Management

**User Story:** As a content producer, I want to create and manage persistent video projects with tracked status and stages, so that I can work on multiple videos over time without losing progress.

#### Acceptance Criteria

1. THE system SHALL allow creating a new project with a title and optional description, assigning a UUID v4 as the project ID
2. THE system SHALL track each project's status as one of: DRAFT, IN_PROGRESS, REVIEW, RENDERED, PUBLISHED
3. THE system SHALL track each project's current pipeline stage as one of: RESEARCH, TOPIC, SCRIPT, AUDIO, VISUAL, RENDER
4. THE system SHALL allow listing all projects with their current status, stage, and timestamps
5. THE system SHALL persist all project data in a SQLite database
6. THE system SHALL allow opening an existing project and resuming work from its current stage
7. THE system SHALL automatically update the project status to IN_PROGRESS when any pipeline stage begins execution

### Requirement 2: Research Stage — API Call Control

**User Story:** As a content producer, I want to trigger individual research sources and review raw results before accepting them, so that I maintain full control over what data feeds into my video topics.

#### Acceptance Criteria

1. THE system SHALL provide individual trigger buttons for each research source: YouTube, Reddit, Google Trends, Yahoo Finance, Wikipedia
2. THE system SHALL display raw results from each API call in a structured format immediately after completion
3. THE system SHALL allow the user to accept or reject individual results from each source
4. THE system SHALL allow the user to manually add a topic that did not come from any API source
5. THE system SHALL trigger cross-referencing analysis only on accepted results when the user initiates it
6. THE system SHALL store all research results (accepted and rejected) as versioned artifacts in the project
7. THE system SHALL display real-time status for each API call (pending, running, completed, failed)

### Requirement 3: Topic Selection with Unique IDs

**User Story:** As a content producer, I want topics identified by unique IDs with rich metadata, so that I can track, compare, and select the best candidates for script generation.

#### Acceptance Criteria

1. THE system SHALL assign each topic a unique ID following the pattern TOPIC-001, TOPIC-002, etc., scoped to the project
2. THE system SHALL allow editing the title of any topic
3. THE system SHALL display metadata for each topic including: source, score, keywords, and RPM estimate
4. THE system SHALL allow selecting multiple topics for script generation
5. THE system SHALL support generating a pitch for a selected topic via GPT-4o-mini
6. THE system SHALL maintain a selection history showing which topics were selected and deselected over time

### Requirement 4: Script Versioning and Refinement

**User Story:** As a content producer, I want to create, edit, and compare multiple script versions per topic, so that I can iteratively refine my video script before committing to production.

#### Acceptance Criteria

1. THE system SHALL support multiple script versions per topic, each with an incrementing version number
2. THE system SHALL allow creating a new script version by pasting text, uploading a file, or duplicating an existing version
3. THE system SHALL convert script text to VideoScript JSON format using the existing ScriptConverter
4. THE system SHALL allow inline editing of individual scenes within a script version, including narration text, visual type, and visual data
5. THE system SHALL allow reordering, adding, and removing scenes within a script version
6. THE system SHALL provide a diff view comparing any two versions of a script
7. THE system SHALL require an explicit finalize action to mark a script version as ready for audio production
8. THE system SHALL store all script versions as artifacts, never overwriting previous versions

### Requirement 5: Audio Script with SRT Timeline

**User Story:** As a content producer, I want an SRT-based audio timeline generated from my finalized script, so that I can fine-tune narration timing, pacing, and voice parameters before synthesis.

#### Acceptance Criteria

1. THE system SHALL generate an SRT-format audio timeline from a finalized script version, using HH:MM:SS,mmm timestamp format
2. THE system SHALL allow editing the narration text of any audio segment at any timestamp
3. THE system SHALL allow adjusting the start and end timing of any audio segment
4. THE system SHALL allow inserting pauses between audio segments
5. THE system SHALL support per-segment voice parameters including speed, pitch, and emphasis, mapped to SSML attributes
6. THE system SHALL allow re-synthesizing individual audio segments without affecting other segments
7. THE system SHALL allow previewing individual audio segments in the browser
8. THE system SHALL store all audio timeline versions as artifacts
9. THE system SHALL display the total duration of the audio timeline

### Requirement 6: Visual Composition Control

**User Story:** As a content producer, I want granular control over each scene's visuals — including stock footage search, overlay editing, and single-scene re-rendering — so that I can craft polished visuals without re-rendering the entire video.

#### Acceptance Criteria

1. THE system SHALL display a thumbnail preview for each scene in the visual editor
2. THE system SHALL integrate Pexels stock footage search, allowing the user to search and select footage per scene
3. THE system SHALL present multiple footage options from Pexels for the user to choose from
4. THE system SHALL allow changing the visual instruction type for any scene
5. THE system SHALL allow editing text overlay content for scenes with text overlays
6. THE system SHALL allow changing overlay position and style properties
7. THE system SHALL support re-rendering a single scene without affecting other scenes
8. THE system SHALL support Manim-based visual effects as a visual type
9. THE system SHALL support configuring transition effects between scenes

### Requirement 7: Background Music

**User Story:** As a content producer, I want to upload background music and control its mix with the narration, so that my videos have professional audio production.

#### Acceptance Criteria

1. THE system SHALL allow uploading background music files in MP3 or WAV format
2. THE system SHALL provide a volume control for background music relative to narration, ranging from 0% to 100%
3. THE system SHALL support fade-in and fade-out duration settings for background music
4. THE system SHALL mix background music with narration audio during the final render
5. THE system SHALL allow previewing the audio mix before rendering

### Requirement 8: Final Render Control

**User Story:** As a content producer, I want to review all scenes, reorder them, and trigger a final render with real-time progress, so that I can produce the finished video with confidence.

#### Acceptance Criteria

1. THE system SHALL display all scenes with thumbnail previews and audio segment previews in the render panel
2. THE system SHALL allow drag-and-drop reordering of scenes in the render panel
3. THE system SHALL allow removing scenes from the final render
4. THE system SHALL render the final concatenated video from all included scenes, audio, and background music
5. THE system SHALL display real-time render progress including percentage and current operation
6. THE system SHALL store the rendered video as a versioned artifact
7. THE system SHALL allow re-rendering after making changes to scenes, audio, or music

### Requirement 9: REST API Backend

**User Story:** As a developer, I want a well-structured FastAPI backend with consistent endpoints, real-time updates, and proper validation, so that the frontend can reliably interact with all pipeline operations.

#### Acceptance Criteria

1. THE system SHALL implement the backend as a FastAPI application with auto-generated OpenAPI documentation
2. THE system SHALL expose REST endpoints for all CRUD operations on projects, topics, scripts, audio segments, scenes, and music
3. THE system SHALL provide a WebSocket endpoint for real-time job status updates per project
4. THE system SHALL execute long-running operations (research, synthesis, rendering) as background tasks
5. THE system SHALL serve static files (rendered videos, audio, thumbnails) from the backend
6. THE system SHALL validate all request payloads using Pydantic models
7. THE system SHALL return consistent error responses with status code, error type, and descriptive message

### Requirement 10: React Frontend

**User Story:** As a content producer, I want a modern, responsive web interface with real-time updates and intuitive navigation, so that I can efficiently manage all aspects of video production.

#### Acceptance Criteria

1. THE system SHALL implement the frontend as a React single-page application with client-side routing
2. THE system SHALL display a project dashboard showing all projects with status badges and key metadata
3. THE system SHALL provide a project workspace with a stage-based navigation sidebar (Research, Topic, Script, Audio, Visual, Render)
4. THE system SHALL support video and audio preview playback within the browser
5. THE system SHALL display real-time job status updates via WebSocket connection
6. THE system SHALL be responsive for viewport widths of 1280px and above
7. THE system SHALL use shadcn/ui as the component library for consistent UI patterns
