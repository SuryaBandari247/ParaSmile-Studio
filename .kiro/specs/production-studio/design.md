# Design Document: Video Production Studio

## Overview

The Video Production Studio replaces the Streamlit-based Pipeline UI with a React SPA frontend communicating via REST and WebSocket to a FastAPI backend. The backend wraps existing pipeline modules (ResearchAgent, ScriptConverter, VoiceSynthesizer, AssetOrchestrator) behind a service layer, persists all data in SQLite, and manages background jobs for long-running operations. The frontend provides a project-based workspace with stage-based navigation, inline editing, and real-time status updates.

### Core Objectives

1. **Project Persistence**: Replace session-only state with SQLite-backed projects that survive restarts
2. **Granular Control**: Individual API triggers, per-scene re-renders, per-segment audio synthesis
3. **Artifact Versioning**: Every script, audio, and visual output is versioned — nothing is overwritten
4. **Real-Time Feedback**: WebSocket-driven job status for all background operations
5. **Module Reuse**: Service layer wraps existing modules without modifying their interfaces

### Design Principles

- **Service Layer Wraps Existing Modules**: ResearchAgent, ScriptConverter, VoiceSynthesizer, AssetOrchestrator are consumed as-is
- **SQLite Stays**: Extends the existing content_store pattern — no database migration to Postgres
- **BackgroundTasks for Short Jobs, Worker Thread for Renders**: FastAPI BackgroundTasks handle research/synthesis; a dedicated worker thread handles video rendering
- **One WebSocket Per Project**: Each open project workspace maintains a single WebSocket connection for all job updates
- **SRT Timeline Format**: Audio segments use SubRip Timing (HH:MM:SS,mmm) for industry-standard compatibility

## Architecture

### System Architecture

```mermaid
graph TD
    subgraph React Frontend
        DASH[Dashboard Page]
        WS_PAGE[Project Workspace]
        subgraph Workspace Panels
            RES[Research Panel]
            TOP[Topic Panel]
            SCR[Script Editor]
            AUD[Audio Editor]
            VIS[Visual Editor]
            REN[Render Panel]
            MUS[Music Mixer]
        end
    end

    subgraph FastAPI Backend
        subgraph API Router Layer
            R_PROJ[projects router]
            R_RES[research router]
            R_TOP[topics router]
            R_SCR[scripts router]
            R_AUD[audio router]
            R_VIS[visuals router]
            R_MUS[music router]
            R_REN[render router]
            R_WS[websocket router]
        end

        subgraph Service Layer
            S_PROJ[ProjectService]
            S_RES[ResearchService]
            S_SCR[ScriptService]
            S_AUD[AudioService]
            S_VIS[VisualService]
            S_REN[RenderService]
            S_JOB[JobRunner]
            S_ART[ArtifactStore]
        end

        subgraph Existing Pipeline Modules
            RA[research_agent/<br/>ResearchAgent]
            SC[script_generator/<br/>ScriptConverter]
            VS[voice_synthesizer/<br/>VoiceSynthesizer]
            AO[asset_orchestrator/<br/>AssetOrchestrator]
            PC[asset_orchestrator/<br/>PexelsClient]
        end
    end

    DB[(SQLite Database<br/>.data/studio.db)]

    DASH -->|REST| R_PROJ
    WS_PAGE -->|REST + WebSocket| R_WS
    RES -->|REST| R_RES
    TOP -->|REST| R_TOP
    SCR -->|REST| R_SCR
    AUD -->|REST| R_AUD
    VIS -->|REST| R_VIS
    MUS -->|REST| R_MUS
    REN -->|REST| R_REN

    R_PROJ --> S_PROJ
    R_RES --> S_RES
    R_TOP --> S_PROJ
    R_SCR --> S_SCR
    R_AUD --> S_AUD
    R_VIS --> S_VIS
    R_REN --> S_REN
    R_MUS --> S_REN

    S_RES --> RA
    S_SCR --> SC
    S_AUD --> VS
    S_VIS --> AO
    S_VIS --> PC
    S_JOB --> DB
    S_ART --> DB
    S_PROJ --> DB


### Data Flow: Project Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as FastAPI
    participant Service as Service Layer
    participant Module as Pipeline Module
    participant DB as SQLite
    participant WS as WebSocket

    User->>Frontend: Create Project
    Frontend->>API: POST /api/projects
    API->>Service: ProjectService.create()
    Service->>DB: INSERT INTO projects
    DB-->>Service: project row
    Service-->>API: Project
    API-->>Frontend: 201 Created

    User->>Frontend: Trigger YouTube Research
    Frontend->>API: POST /api/projects/{id}/research/youtube
    API->>Service: ResearchService.search_youtube()
    Service->>DB: INSERT INTO jobs (status=RUNNING)
    Service->>WS: broadcast job_started
    Service->>Module: ResearchAgent (YouTube only)
    Module-->>Service: raw results
    Service->>DB: UPDATE jobs (status=COMPLETED)
    Service->>DB: INSERT INTO artifacts
    Service->>WS: broadcast job_completed
    API-->>Frontend: 202 Accepted + job_id

    User->>Frontend: Finalize Script
    Frontend->>API: POST /api/projects/{id}/scripts/{vid}/finalize
    API->>Service: ScriptService.finalize()
    Service->>DB: UPDATE script_versions SET is_finalized=1
    Service-->>API: ScriptVersion
    API-->>Frontend: 200 OK

    User->>Frontend: Start Final Render
    Frontend->>API: POST /api/projects/{id}/render
    API->>Service: RenderService.start_render()
    Service->>DB: INSERT INTO jobs (status=RUNNING)
    Service->>WS: broadcast render_started
    Service->>Module: FFmpegCompositor (worker thread)
    loop Progress Updates
        Module-->>Service: progress %
        Service->>WS: broadcast render_progress
    end
    Module-->>Service: output path
    Service->>DB: UPDATE jobs, INSERT INTO artifacts
    Service->>WS: broadcast render_completed
    API-->>Frontend: 202 Accepted + job_id
```

## Data Models

### SQLite Schema

```sql
-- File: studio_api/migrations/001_initial.sql
-- Executed on startup by migration runner

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT    PRIMARY KEY,  -- UUID v4
    title           TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'DRAFT',      -- DRAFT|IN_PROGRESS|REVIEW|RENDERED|PUBLISHED
    current_stage   TEXT    NOT NULL DEFAULT 'RESEARCH',   -- RESEARCH|TOPIC|SCRIPT|AUDIO|VISUAL|RENDER
    created_at      TEXT    NOT NULL,  -- ISO 8601 UTC
    updated_at      TEXT    NOT NULL   -- ISO 8601 UTC
);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT    PRIMARY KEY,  -- UUID v4
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    job_type        TEXT    NOT NULL,     -- research_youtube|research_reddit|research_trends|research_finance|research_wikipedia|cross_reference|synthesize_audio|render_scene|render_final|generate_pitch
    status          TEXT    NOT NULL DEFAULT 'PENDING',  -- PENDING|RUNNING|COMPLETED|FAILED
    input_json      TEXT,                -- JSON payload of job input parameters
    output_json     TEXT,                -- JSON payload of job results
    error           TEXT,                -- error message if FAILED
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    job_id          TEXT    REFERENCES jobs(id),
    artifact_type   TEXT    NOT NULL,    -- research_results|topic_list|script_json|audio_segment|audio_timeline|scene_render|scene_thumbnail|final_render|music_file
    version         INTEGER NOT NULL DEFAULT 1,
    file_path       TEXT    NOT NULL,
    metadata_json   TEXT,                -- JSON with type-specific metadata
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id              TEXT    PRIMARY KEY,  -- TOPIC-001 pattern
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    title           TEXT    NOT NULL,
    source          TEXT    NOT NULL,     -- youtube|reddit|google_trends|yahoo_finance|wikipedia|manual
    score           REAL    DEFAULT 0.0,
    keywords_json   TEXT,                -- JSON array of keyword strings
    status          TEXT    NOT NULL DEFAULT 'PENDING',  -- PENDING|SELECTED|REJECTED
    metadata_json   TEXT,                -- JSON with source-specific data (RPM estimate, trend_score, etc.)
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS script_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    topic_id        TEXT    NOT NULL REFERENCES topics(id),
    version         INTEGER NOT NULL,
    title           TEXT    NOT NULL,
    script_json     TEXT    NOT NULL,     -- Full VideoScript JSON
    is_finalized    INTEGER NOT NULL DEFAULT 0,  -- 0 or 1
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    script_version_id INTEGER NOT NULL REFERENCES script_versions(id),
    scene_number    INTEGER NOT NULL,
    start_time      TEXT    NOT NULL,     -- SRT format: HH:MM:SS,mmm
    end_time        TEXT    NOT NULL,     -- SRT format: HH:MM:SS,mmm
    narration_text  TEXT    NOT NULL,
    voice_params_json TEXT,              -- JSON: {speed, pitch, emphasis} mapped to SSML
    audio_file_path TEXT,                -- path to synthesized MP3, NULL if not yet synthesized
    status          TEXT    NOT NULL DEFAULT 'PENDING',  -- PENDING|SYNTHESIZED|FAILED
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id),
    scene_number    INTEGER NOT NULL,
    visual_type     TEXT    NOT NULL,     -- manim_animation|stock_footage|text_overlay|chart|screen_recording
    visual_data_json TEXT   NOT NULL,     -- JSON with type-specific visual instruction data
    stock_video_path TEXT,               -- path to selected Pexels footage
    rendered_path   TEXT,                -- path to rendered scene MP4
    thumbnail_path  TEXT,                -- path to thumbnail PNG
    status          TEXT    NOT NULL DEFAULT 'PENDING',  -- PENDING|RENDERED|FAILED
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_topics_project ON topics(project_id);
CREATE INDEX IF NOT EXISTS idx_script_versions_project ON script_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_script_versions_topic ON script_versions(topic_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_project ON audio_segments(project_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_script ON audio_segments(script_version_id);
CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id);
```

## API Endpoints

### Projects

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/projects` | Create a new project | 201 + Project |
| GET | `/api/projects` | List all projects | 200 + Project[] |
| GET | `/api/projects/{id}` | Get project details | 200 + Project |
| PATCH | `/api/projects/{id}` | Update project fields | 200 + Project |
| DELETE | `/api/projects/{id}` | Delete project and all related data | 204 |

### Research

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/projects/{id}/research/youtube` | Trigger YouTube research | 202 + Job |
| POST | `/api/projects/{id}/research/reddit` | Trigger Reddit research | 202 + Job |
| POST | `/api/projects/{id}/research/trends` | Trigger Google Trends research | 202 + Job |
| POST | `/api/projects/{id}/research/finance` | Trigger Yahoo Finance research | 202 + Job |
| POST | `/api/projects/{id}/research/wikipedia` | Trigger Wikipedia research | 202 + Job |
| POST | `/api/projects/{id}/research/cross-reference` | Cross-reference accepted results | 202 + Job |
| GET | `/api/projects/{id}/research/results` | Get all research results | 200 + ResearchResults |

### Topics

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/projects/{id}/topics` | List topics for project | 200 + Topic[] |
| POST | `/api/projects/{id}/topics` | Create a manual topic | 201 + Topic |
| PATCH | `/api/projects/{id}/topics/{topic_id}` | Update topic (title, status) | 200 + Topic |
| DELETE | `/api/projects/{id}/topics/{topic_id}` | Delete a topic | 204 |
| POST | `/api/projects/{id}/topics/{topic_id}/pitch` | Generate pitch via GPT-4o-mini | 202 + Job |

### Scripts

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/projects/{id}/scripts` | List all script versions | 200 + ScriptVersion[] |
| POST | `/api/projects/{id}/scripts` | Create a new script version | 201 + ScriptVersion |
| GET | `/api/projects/{id}/scripts/{version_id}` | Get script version details | 200 + ScriptVersion |
| PATCH | `/api/projects/{id}/scripts/{version_id}` | Update script content | 200 + ScriptVersion |
| POST | `/api/projects/{id}/scripts/{version_id}/finalize` | Finalize a script version | 200 + ScriptVersion |
| GET | `/api/projects/{id}/scripts/diff?v1={id1}&v2={id2}` | Diff two script versions | 200 + DiffResult |

### Audio

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/projects/{id}/audio/timeline` | Generate SRT timeline from finalized script | 201 + AudioTimeline |
| GET | `/api/projects/{id}/audio/segments` | List all audio segments | 200 + AudioSegment[] |
| PATCH | `/api/projects/{id}/audio/segments/{seg_id}` | Update segment text/timing/params | 200 + AudioSegment |
| POST | `/api/projects/{id}/audio/segments/{seg_id}/synthesize` | Synthesize a single segment | 202 + Job |
| GET | `/api/projects/{id}/audio/segments/{seg_id}/preview` | Stream audio preview | 200 + audio/mpeg |
| POST | `/api/projects/{id}/audio/segments/{seg_id}/pause` | Insert pause after segment | 201 + AudioSegment |

### Visuals

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/projects/{id}/scenes` | List all scenes | 200 + Scene[] |
| PATCH | `/api/projects/{id}/scenes/{scene_id}` | Update scene visual type/data | 200 + Scene |
| POST | `/api/projects/{id}/scenes/{scene_id}/search-footage` | Search Pexels for footage | 200 + FootageResult[] |
| POST | `/api/projects/{id}/scenes/{scene_id}/select-footage` | Select footage for scene | 200 + Scene |
| POST | `/api/projects/{id}/scenes/{scene_id}/render` | Render a single scene | 202 + Job |
| GET | `/api/projects/{id}/scenes/{scene_id}/preview` | Stream scene preview | 200 + video/mp4 |

### Music

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/projects/{id}/music/upload` | Upload background music file | 201 + MusicFile |
| PATCH | `/api/projects/{id}/music/settings` | Update volume, fade-in, fade-out | 200 + MusicSettings |
| GET | `/api/projects/{id}/music/preview` | Preview audio mix | 200 + audio/mpeg |

### Render

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/projects/{id}/render` | Start final render | 202 + Job |
| GET | `/api/projects/{id}/render/status` | Get render job status | 200 + Job |
| GET | `/api/projects/{id}/render/output` | Stream/download rendered video | 200 + video/mp4 |
| POST | `/api/projects/{id}/render/reorder` | Update scene order for render | 200 + SceneOrder |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws/projects/{id}` | Per-project WebSocket for real-time job status updates |

WebSocket message format:
```json
{
    "event": "job_started|job_progress|job_completed|job_failed",
    "job_id": "uuid",
    "job_type": "research_youtube|synthesize_audio|render_scene|render_final|...",
    "data": {
        "progress": 0.75,
        "message": "Rendering scene 3 of 7...",
        "output": {}
    }
}
```

## Frontend Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── App.tsx                          # Root component with router
│   ├── main.tsx                         # Entry point
│   ├── api/
│   │   ├── client.ts                    # Axios instance with base URL, error interceptor
│   │   ├── projects.ts                  # Project CRUD API calls
│   │   ├── research.ts                  # Research trigger + results API calls
│   │   ├── scripts.ts                   # Script CRUD + finalize + diff API calls
│   │   ├── audio.ts                     # Audio timeline + segment + synthesize API calls
│   │   ├── visuals.ts                   # Scene CRUD + footage search + render API calls
│   │   └── websocket.ts                # WebSocket client with reconnect logic
│   ├── pages/
│   │   ├── Dashboard.tsx                # Project list with create dialog
│   │   └── ProjectWorkspace.tsx         # Stage-based workspace shell
│   ├── components/
│   │   ├── research/
│   │   │   ├── SourceTriggerButtons.tsx # Individual API source buttons with status
│   │   │   ├── ResultsDisplay.tsx       # Raw results with accept/reject
│   │   │   └── ManualTopicInput.tsx     # Manual topic addition form
│   │   ├── topics/
│   │   │   ├── TopicList.tsx            # Topic cards with metadata
│   │   │   ├── TopicEditor.tsx          # Inline title editing
│   │   │   └── PitchGenerator.tsx       # Pitch generation trigger + display
│   │   ├── script/
│   │   │   ├── VersionList.tsx          # Script version list + creation
│   │   │   ├── SceneEditor.tsx          # Inline scene editing (narration, visual)
│   │   │   ├── SceneReorder.tsx         # Drag-and-drop scene reordering
│   │   │   ├── DiffView.tsx             # Side-by-side version diff
│   │   │   └── FinalizeButton.tsx       # Explicit finalize action
│   │   ├── audio/
│   │   │   ├── SRTTimeline.tsx          # Timeline display with segments
│   │   │   ├── SegmentEditor.tsx        # Text, timing, voice param editing
│   │   │   ├── VoiceParamControls.tsx   # Speed, pitch, emphasis sliders
│   │   │   └── AudioPreview.tsx         # Per-segment audio playback
│   │   ├── visual/
│   │   │   ├── SceneGrid.tsx            # Scene thumbnails grid
│   │   │   ├── FootageSearch.tsx        # Pexels search + selection
│   │   │   ├── VisualTypeEditor.tsx     # Visual type/data editing
│   │   │   └── TransitionControls.tsx   # Transition effect configuration
│   │   ├── render/
│   │   │   ├── RenderSceneList.tsx      # Scenes with drag-and-drop reorder
│   │   │   ├── RenderProgress.tsx       # Real-time progress display
│   │   │   └── VideoPreview.tsx         # Final video playback + download
│   │   ├── music/
│   │   │   ├── MusicUpload.tsx          # MP3/WAV upload
│   │   │   ├── MixControls.tsx          # Volume, fade-in, fade-out
│   │   │   └── MixPreview.tsx           # Audio mix preview
│   │   └── common/
│   │       ├── StatusBadge.tsx          # Project/job status badges
│   │       ├── JobStatusIndicator.tsx   # Real-time job status display
│   │       └── StageNavigation.tsx      # Stage-based sidebar navigation
│   ├── hooks/
│   │   ├── useWebSocket.ts             # WebSocket connection hook
│   │   ├── useProject.ts               # Project data fetching hook
│   │   └── useJobStatus.ts             # Job status polling/WS hook
│   ├── store/
│   │   └── projectStore.ts             # Client-side project state (Zustand or context)
│   └── types/
│       └── index.ts                     # TypeScript interfaces matching Pydantic models
```

## Backend Structure

```
studio_api/
├── __init__.py
├── main.py                              # FastAPI app factory, CORS, static files, startup
├── config.py                            # Settings from env vars, paths, defaults
├── database.py                          # SQLite connection, migration runner, helpers
├── models/
│   ├── __init__.py
│   ├── project.py                       # ProjectCreate, ProjectUpdate, ProjectResponse
│   ├── topic.py                         # TopicCreate, TopicUpdate, TopicResponse
│   ├── script.py                        # ScriptVersionCreate, ScriptVersionResponse, DiffResult
│   ├── audio.py                         # AudioSegmentCreate, AudioSegmentUpdate, AudioTimelineResponse
│   ├── scene.py                         # SceneUpdate, SceneResponse, FootageResult
│   └── job.py                           # JobResponse, JobStatus enum
├── routers/
│   ├── __init__.py
│   ├── projects.py                      # /api/projects CRUD
│   ├── research.py                      # /api/projects/{id}/research/* triggers
│   ├── topics.py                        # /api/projects/{id}/topics CRUD + pitch
│   ├── scripts.py                       # /api/projects/{id}/scripts CRUD + finalize + diff
│   ├── audio.py                         # /api/projects/{id}/audio/* timeline + segments
│   ├── visuals.py                       # /api/projects/{id}/scenes/* CRUD + search + render
│   ├── music.py                         # /api/projects/{id}/music/* upload + settings
│   ├── render.py                        # /api/projects/{id}/render start + status + output
│   └── websocket.py                     # /ws/projects/{id} connection manager
├── services/
│   ├── __init__.py
│   ├── project_service.py               # Project CRUD, status/stage transitions
│   ├── research_service.py              # Wraps ResearchAgent for per-source calls
│   ├── script_service.py                # Wraps ScriptConverter, version management, diff
│   ├── audio_service.py                 # Wraps VoiceSynthesizer, SRT timeline generation
│   ├── visual_service.py               # Wraps AssetOrchestrator + PexelsClient
│   ├── render_service.py               # Final composition, scene ordering, music mixing
│   ├── job_runner.py                    # Job lifecycle management, status broadcasting
│   └── artifact_store.py               # Versioned file storage, path management
└── migrations/
    └── 001_initial.sql                  # Full schema from Data Models section
```

## Key Design Decisions

### 1. SQLite Stays

The existing `content_store` uses SQLite at `.data/content_store.db`. The studio extends this pattern with a separate `.data/studio.db` database. SQLite is sufficient for a local production tool — no concurrent multi-user access, WAL mode handles read/write overlap, and the schema is simple enough that an ORM adds no value. Raw `sqlite3` with `Row` factory keeps things lightweight.

### 2. BackgroundTasks for Short Jobs, Worker Thread for Renders

FastAPI's `BackgroundTasks` handles operations that complete in seconds to low minutes (API research calls, single audio segment synthesis, pitch generation). Video rendering — which can take minutes to hours — runs in a dedicated worker thread managed by `job_runner.py` to avoid blocking the async event loop. Both paths update job status in the database and broadcast via WebSocket.

### 3. One WebSocket Per Project

When a user opens a project workspace, the frontend establishes a single WebSocket connection to `/ws/projects/{id}`. All job status events for that project are broadcast through this connection. The `ConnectionManager` in `websocket.py` tracks active connections per project and handles reconnection gracefully. This avoids polling and keeps the UI responsive.

### 4. Artifact Versioning — Nothing Overwritten

Every pipeline output (script JSON, audio MP3, scene MP4, thumbnail PNG) is stored as a versioned artifact. The `artifact_store.py` service manages file paths using the pattern: `.data/artifacts/{project_id}/{artifact_type}/v{version}/{filename}`. Previous versions are never deleted or overwritten, enabling rollback and comparison.

### 5. Service Layer Wraps Existing Modules

Each service class composes (not inherits) the corresponding pipeline module:
- `ResearchService` → `ResearchAgent` (per-source method calls)
- `ScriptService` → `ScriptConverter` (convert + serialize)
- `AudioService` → `VoiceSynthesizer` (per-segment synthesis)
- `VisualService` → `AssetOrchestrator` + `PexelsClient` (render + search)

The service layer adds: database persistence, job tracking, artifact storage, and WebSocket notifications. The underlying modules are unmodified.

### 6. SRT Timeline Format

Audio segments use SubRip Timing format (`HH:MM:SS,mmm`) because it's an industry standard, human-readable, and trivially parseable. The `audio_service.py` generates the initial timeline by estimating duration from word count (150 WPM baseline), then the user adjusts timing in the editor. Voice parameters (speed, pitch, emphasis) are stored as JSON and mapped to SSML attributes at synthesis time.

### 7. Single-Scene Re-Render

The visual editor supports re-rendering individual scenes without touching others. Each scene has its own `rendered_path` and `status`. When a scene is re-rendered, only that scene's job runs, and the render panel shows the updated thumbnail. The final render concatenates all scene outputs in order — so a single-scene change only requires re-rendering that scene plus the final concatenation.

### 8. Topic ID Pattern

Topics use a project-scoped sequential ID pattern (`TOPIC-001`, `TOPIC-002`, etc.) instead of UUIDs. This makes topics human-readable in the UI and in conversation. The next ID is computed by querying `MAX(id)` for the project and incrementing.

## Correctness Properties

### Property 1: Project UUID uniqueness

*For any* two projects created via `ProjectService.create()`, their assigned UUIDs shall be distinct.

**Validates: Requirements 1.1**

### Property 2: Project status transitions are valid

*For any* project, status transitions shall only follow valid paths: DRAFT → IN_PROGRESS → REVIEW → RENDERED → PUBLISHED. The status shall never skip a state or move backward.

**Validates: Requirements 1.2, 1.7**

### Property 3: Topic ID sequential uniqueness

*For any* project with N topics, the topic IDs shall be TOPIC-001 through TOPIC-N with no gaps or duplicates within the project scope.

**Validates: Requirements 3.1**

### Property 4: Script version immutability after finalization

*For any* finalized script version, subsequent update attempts shall be rejected. The `script_json` and `is_finalized` fields shall not change after finalization.

**Validates: Requirements 4.7, 4.8**

### Property 5: Artifact version monotonicity

*For any* artifact type within a project, version numbers shall be strictly increasing. Creating a new artifact shall assign `max(existing_versions) + 1` as the version number.

**Validates: Requirements 4.8, 5.8, 8.6**

### Property 6: SRT timestamp ordering

*For any* audio timeline, the segments shall be ordered by `start_time`, and for every consecutive pair of segments (A, B), `A.end_time <= B.start_time` shall hold (no overlapping segments).

**Validates: Requirements 5.1, 5.3**

### Property 7: Audio segment independence

*For any* audio segment re-synthesis, only the targeted segment's `audio_file_path` and `status` shall change. All other segments in the same timeline shall remain unmodified.

**Validates: Requirements 5.6**

### Property 8: Scene render isolation

*For any* single-scene render operation, only the targeted scene's `rendered_path`, `thumbnail_path`, and `status` shall change. All other scenes in the project shall remain unmodified.

**Validates: Requirements 6.7**

### Property 9: Job status lifecycle

*For any* job, the status shall transition only through: PENDING → RUNNING → COMPLETED or PENDING → RUNNING → FAILED. No other transitions shall occur.

**Validates: Requirements 9.3, 9.4**

### Property 10: WebSocket message completeness

*For any* job that transitions to COMPLETED or FAILED, exactly one corresponding WebSocket event shall be broadcast to all connections for that project.

**Validates: Requirements 9.3, 10.5**

### Property 11: Research result persistence

*For any* research API call (accepted or rejected), the raw results shall be stored as an artifact. Rejecting a result shall not delete it from storage.

**Validates: Requirements 2.6**

### Property 12: Scene order consistency

*For any* render reorder operation, the resulting scene order shall be a valid permutation of the existing scene IDs with no duplicates or missing entries.

**Validates: Requirements 8.2, 8.3**

## Error Handling

### Error Response Format

All API errors return a consistent JSON structure:

```json
{
    "error": {
        "type": "validation_error|not_found|conflict|internal_error|job_failed",
        "message": "Human-readable description",
        "details": {}
    }
}
```

### Error Classification

| Category | HTTP Status | Error Type | Examples |
|----------|-------------|------------|----------|
| Validation | 422 | `validation_error` | Invalid project status, malformed SRT time, missing required field |
| Not Found | 404 | `not_found` | Project/topic/script/scene ID doesn't exist |
| Conflict | 409 | `conflict` | Duplicate topic ID, finalized script edit attempt, job already running |
| External Service | 502 | `external_error` | YouTube API failure, ElevenLabs timeout, Pexels rate limit |
| Internal | 500 | `internal_error` | Database error, file system error, unexpected exception |

### WebSocket Error Events

Job failures are broadcast as `job_failed` events with the error message and job type, allowing the frontend to display contextual error information in the relevant panel.

## Testing Strategy

### Backend Tests

- **Unit tests**: `pytest` — test each service in isolation with mocked pipeline modules and in-memory SQLite
- **Property-based tests**: `hypothesis` — test correctness properties (UUID uniqueness, status transitions, SRT ordering, artifact versioning)
- **Integration tests**: Test router → service → database flow with a temporary SQLite database

### Frontend Tests

- **Component tests**: Vitest + React Testing Library — test individual components with mocked API responses
- **Integration tests**: Test page-level flows (create project → navigate stages → trigger operations)

### Test File Organization

```
tests/
├── unit/
│   ├── test_project_service.py
│   ├── test_research_service.py
│   ├── test_script_service.py
│   ├── test_audio_service.py
│   ├── test_visual_service.py
│   ├── test_render_service.py
│   ├── test_job_runner.py
│   └── test_artifact_store.py
├── property/
│   └── test_studio_props.py
├── integration/
│   └── test_studio_api.py
frontend/
└── src/
    └── __tests__/
        ├── Dashboard.test.tsx
        ├── ProjectWorkspace.test.tsx
        └── components/
            └── ...
```
