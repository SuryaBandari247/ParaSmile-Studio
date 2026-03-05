# Implementation Plan: Video Production Studio

## Overview

Build the Video Production Studio — a React frontend + FastAPI backend that replaces the Streamlit Pipeline UI. Implementation proceeds bottom-up: backend foundation → domain endpoints → WebSocket → frontend foundation → frontend workspace panels. The backend wraps existing pipeline modules (ResearchAgent, ScriptConverter, VoiceSynthesizer, AssetOrchestrator) behind a service layer with SQLite persistence and background job management.

## Tasks

### Phase 1: Backend Foundation (FastAPI + Database)

- [x] 1. Set up FastAPI project structure
  - [x] 1.1 Create `studio_api/` package with `__init__.py`, `main.py`, `config.py`, `database.py`
    - _Requirements: R9.1_
  - [x] 1.2 Configure FastAPI app with CORS middleware, static file serving, and OpenAPI docs
    - _Requirements: R9.1, R9.5_
  - [x] 1.3 Add FastAPI, uvicorn, pydantic, and websockets dependencies to `requirements.txt`
    - _Requirements: R9.1_
  - [x] 1.4 Create `database.py` with SQLite connection helper (WAL mode, foreign keys) and migration runner
    - _Requirements: R9.1, R1.5_

- [x] 2. Database schema and migrations
  - [x] 2.1 Create `studio_api/migrations/001_initial.sql` with all tables (projects, jobs, artifacts, topics, script_versions, audio_segments, scenes) and indexes
    - _Requirements: R1.5_
  - [x] 2.2 Implement auto-migration on startup in `database.py` — read and execute SQL files from migrations/ directory
    - _Requirements: R1.5_

- [x] 3. Pydantic models
  - [x] 3.1 Create `studio_api/models/project.py` — ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStatus enum, PipelineStage enum
    - _Requirements: R9.6_
  - [x] 3.2 Create `studio_api/models/topic.py` — TopicCreate, TopicUpdate, TopicResponse, TopicStatus enum
    - _Requirements: R9.6_
  - [x] 3.3 Create `studio_api/models/script.py` — ScriptVersionCreate, ScriptVersionUpdate, ScriptVersionResponse, DiffResult
    - _Requirements: R9.6_
  - [x] 3.4 Create `studio_api/models/audio.py` — AudioSegmentCreate, AudioSegmentUpdate, AudioSegmentResponse, AudioTimelineResponse, VoiceParams
    - _Requirements: R9.6_
  - [x] 3.5 Create `studio_api/models/scene.py` — SceneUpdate, SceneResponse, FootageResult, MusicSettings
    - _Requirements: R9.6_
  - [x] 3.6 Create `studio_api/models/job.py` — JobResponse, JobStatus enum, JobType enum, WebSocketMessage
    - _Requirements: R9.6_

- [x] 4. Project service and router
  - [x] 4.1 Implement `studio_api/services/project_service.py` — create (UUID generation), get, list, update, delete with SQLite persistence and status/stage transitions
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.6, R1.7_
  - [x] 4.2 Implement `studio_api/routers/projects.py` — POST, GET (list), GET (detail), PATCH, DELETE endpoints with Pydantic validation and consistent error responses
    - _Requirements: R9.2, R9.6, R9.7_
  - [x] 4.3 Write unit tests for project service and router (`tests/unit/test_project_service.py`)
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6, R1.7_

- [x] 5. Job runner and artifact store
  - [x] 5.1 Implement `studio_api/services/job_runner.py` — create job, update status, run in BackgroundTasks or worker thread, broadcast status via WebSocket
    - _Requirements: R9.3, R9.4_
  - [x] 5.2 Implement `studio_api/services/artifact_store.py` — versioned file storage at `.data/artifacts/{project_id}/{type}/v{version}/{filename}`, create/get/list artifacts
    - _Requirements: R4.8, R5.8, R8.6_
  - [x] 5.3 Write unit tests for job runner and artifact store (`tests/unit/test_job_runner.py`, `tests/unit/test_artifact_store.py`)
    - _Requirements: R9.3, R9.4_

### Phase 2: Research and Topic Endpoints

- [x] 6. Research service and router
  - [x] 6.1 Implement `studio_api/services/research_service.py` wrapping ResearchAgent with per-source methods (search_youtube, search_reddit, search_trends, search_finance, search_wikipedia, cross_reference)
    - _Requirements: R2.1, R2.5, R2.6_
  - [x] 6.2 Implement `studio_api/routers/research.py` with individual source trigger endpoints, cross-reference endpoint, and results retrieval
    - _Requirements: R2.1, R2.2, R2.3, R2.5, R2.7_
  - [x] 6.3 Write unit tests for research service and router (`tests/unit/test_research_service.py`)
    - _Requirements: R2.1, R2.2, R2.3, R2.4, R2.5, R2.6, R2.7_

- [x] 7. Topic service and router
  - [x] 7.1 Implement `studio_api/services/topic_service.py` (within project_service or standalone) with TOPIC-001 sequential ID generation, CRUD, status management, and pitch generation via GPT-4o-mini
    - _Requirements: R3.1, R3.2, R3.3, R3.4, R3.5, R3.6_
  - [x] 7.2 Implement `studio_api/routers/topics.py` with CRUD endpoints, pitch generation trigger, and topic status updates
    - _Requirements: R3.1, R3.2, R3.3, R3.4, R3.5, R3.6_
  - [x] 7.3 Write unit tests for topic service and router (`tests/unit/test_topic_service.py`)
    - _Requirements: R3.1, R3.2, R3.3, R3.4, R3.5, R3.6_

### Phase 3: Script and Audio Endpoints

- [x] 8. Script service and router
  - [x] 8.1 Implement `studio_api/services/script_service.py` wrapping ScriptConverter — create version (paste/upload/duplicate), convert to VideoScript JSON, inline scene editing, finalize, diff between versions
    - _Requirements: R4.1, R4.2, R4.3, R4.4, R4.5, R4.6, R4.7, R4.8_
  - [x] 8.2 Implement `studio_api/routers/scripts.py` with CRUD, finalize, and diff endpoints
    - _Requirements: R4.1, R4.2, R4.3, R4.4, R4.5, R4.6, R4.7, R4.8_
  - [x] 8.3 Write unit tests for script service and router (`tests/unit/test_script_service.py`)
    - _Requirements: R4.1, R4.2, R4.3, R4.4, R4.5, R4.6, R4.7, R4.8_

- [x] 9. Audio service and router
  - [x] 9.1 Implement `studio_api/services/audio_service.py` wrapping VoiceSynthesizer — generate SRT timeline from finalized script, per-segment synthesis, voice params to SSML mapping, pause insertion
    - _Requirements: R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R5.8, R5.9_
  - [x] 9.2 Implement `studio_api/routers/audio.py` with timeline generation, segment CRUD, synthesize, preview, and pause endpoints
    - _Requirements: R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R5.7, R5.8, R5.9_
  - [x] 9.3 Implement SRT format utilities — parse/format HH:MM:SS,mmm timestamps, validate ordering, compute total duration
    - _Requirements: R5.1, R5.3, R5.9_
  - [x] 9.4 Write unit tests for audio service, router, and SRT utilities (`tests/unit/test_audio_service.py`)
    - _Requirements: R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R5.7, R5.8, R5.9_

### Phase 4: Visual and Render Endpoints

- [x] 10. Visual service and router
  - [x] 10.1 Implement `studio_api/services/visual_service.py` wrapping AssetOrchestrator and PexelsClient — scene CRUD, Pexels footage search/selection, single-scene render, thumbnail generation, transition config
    - _Requirements: R6.1, R6.2, R6.3, R6.4, R6.5, R6.6, R6.7, R6.8, R6.9_
  - [x] 10.2 Implement `studio_api/routers/visuals.py` with scene CRUD, search-footage, select-footage, render, and preview endpoints
    - _Requirements: R6.1, R6.2, R6.3, R6.4, R6.5, R6.6, R6.7, R6.8, R6.9_
  - [x] 10.3 Write unit tests for visual service and router (`tests/unit/test_visual_service.py`)
    - _Requirements: R6.1, R6.2, R6.3, R6.4, R6.5, R6.6, R6.7, R6.8, R6.9_

- [x] 11. Music and render endpoints
  - [x] 11.1 Implement `studio_api/routers/music.py` with upload (MP3/WAV), settings (volume/fade), and preview endpoints
    - _Requirements: R7.1, R7.2, R7.3, R7.5_
  - [x] 11.2 Implement `studio_api/services/render_service.py` — final video composition (concatenate scenes + audio + music), scene reordering, music mixing, progress tracking
    - _Requirements: R7.4, R8.1, R8.2, R8.3, R8.4, R8.5, R8.6, R8.7_
  - [x] 11.3 Implement `studio_api/routers/render.py` with start render, status, output download, and reorder endpoints
    - _Requirements: R8.1, R8.2, R8.3, R8.4, R8.5, R8.6, R8.7_
  - [x] 11.4 Write unit tests for music router, render service, and render router (`tests/unit/test_render_service.py`)
    - _Requirements: R7.1, R7.2, R7.3, R7.4, R7.5, R8.1, R8.2, R8.3, R8.4, R8.5, R8.6, R8.7_

### Phase 5: WebSocket and Real-time Updates

- [x] 12. WebSocket implementation
  - [x] 12.1 Implement `studio_api/routers/websocket.py` with ConnectionManager (per-project connection tracking, broadcast, reconnect handling) and `/ws/projects/{id}` endpoint
    - _Requirements: R9.3_
  - [x] 12.2 Integrate WebSocket broadcasting into job_runner.py — emit job_started, job_progress, job_completed, job_failed events
    - _Requirements: R9.3, R10.5_
  - [x] 12.3 Write unit tests for WebSocket connection manager and event broadcasting (`tests/unit/test_websocket.py`)
    - _Requirements: R9.3, R10.5_

### Phase 6: React Frontend — Foundation

- [x] 13. Frontend project setup
  - [x] 13.1 Create Vite + React + TypeScript project in `frontend/` directory with `npm create vite@latest`
    - _Requirements: R10.1_
  - [x] 13.2 Install dependencies: shadcn/ui, react-router-dom, axios, tailwindcss, and configure component library
    - _Requirements: R10.7_
  - [x] 13.3 Configure Vite proxy to forward `/api` and `/ws` requests to FastAPI backend (localhost:8000)
    - _Requirements: R10.1_
  - [x] 13.4 Set up project structure: `src/api/`, `src/pages/`, `src/components/`, `src/hooks/`, `src/store/`, `src/types/`
    - _Requirements: R10.1_

- [x] 14. API client layer
  - [x] 14.1 Implement `src/api/client.ts` — Axios instance with base URL, error interceptor, response typing
    - _Requirements: R10.1_
  - [x] 14.2 Implement `src/api/projects.ts` — createProject, listProjects, getProject, updateProject, deleteProject
    - _Requirements: R10.2_
  - [x] 14.3 Implement `src/api/research.ts` — triggerSource, getResults, crossReference
    - _Requirements: R10.3_
  - [x] 14.4 Implement `src/api/scripts.ts` — listVersions, createVersion, updateVersion, finalize, getDiff
    - _Requirements: R10.3_
  - [x] 14.5 Implement `src/api/audio.ts` — generateTimeline, listSegments, updateSegment, synthesize, getPreviewUrl
    - _Requirements: R10.4_
  - [x] 14.6 Implement `src/api/visuals.ts` — listScenes, updateScene, searchFootage, selectFootage, renderScene, getPreviewUrl
    - _Requirements: R10.4_
  - [x] 14.7 Implement `src/api/websocket.ts` — WebSocket client with auto-reconnect, event parsing, connection lifecycle
    - _Requirements: R10.5_

- [x] 15. Dashboard page
  - [x] 15.1 Implement `src/pages/Dashboard.tsx` — project list with status badges (StatusBadge component), stage indicators, and timestamps
    - _Requirements: R10.2_
  - [x] 15.2 Implement create project dialog — form with title and description fields, calls createProject API
    - _Requirements: R10.2_
  - [x] 15.3 Implement project filtering by status and sorting by date/title
    - _Requirements: R10.2_

### Phase 7: React Frontend — Project Workspace

- [x] 16. Project workspace layout
  - [x] 16.1 Implement `src/components/common/StageNavigation.tsx` — stage-based sidebar with icons, active state, and stage completion indicators (RESEARCH → TOPIC → SCRIPT → AUDIO → VISUAL → RENDER)
    - _Requirements: R10.3_
  - [x] 16.2 Implement `src/pages/ProjectWorkspace.tsx` — workspace shell with sidebar navigation, stage-based routing, WebSocket connection on mount, project header with status
    - _Requirements: R10.3, R10.5_

- [x] 17. Research panel
  - [x] 17.1 Implement `src/components/research/SourceTriggerButtons.tsx` — individual buttons for YouTube, Reddit, Google Trends, Yahoo Finance, Wikipedia with per-source status indicators (pending, running, completed, failed)
    - _Requirements: R2.1, R2.7_
  - [x] 17.2 Implement `src/components/research/ResultsDisplay.tsx` — structured display of raw results with accept/reject buttons per result
    - _Requirements: R2.2, R2.3_
  - [x] 17.3 Implement `src/components/research/ManualTopicInput.tsx` — form for manually adding a topic with title and metadata
    - _Requirements: R2.4_
  - [x] 17.4 Implement cross-reference trigger button that initiates cross-referencing on accepted results
    - _Requirements: R2.5_

- [x] 18. Topic selection panel
  - [x] 18.1 Implement `src/components/topics/TopicList.tsx` — topic cards displaying ID (TOPIC-001), title, source, score, keywords, RPM estimate, and selection status
    - _Requirements: R3.1, R3.3_
  - [x] 18.2 Implement `src/components/topics/TopicEditor.tsx` — inline title editing with save/cancel
    - _Requirements: R3.2_
  - [x] 18.3 Implement topic select/reject actions with multi-select support for script generation
    - _Requirements: R3.4_
  - [x] 18.4 Implement `src/components/topics/PitchGenerator.tsx` — pitch generation trigger and display
    - _Requirements: R3.5_

- [x] 19. Script editor
  - [x] 19.1 Implement `src/components/script/VersionList.tsx` — version list with creation options (paste, upload, duplicate)
    - _Requirements: R4.1, R4.2_
  - [x] 19.2 Implement `src/components/script/SceneEditor.tsx` — inline scene editing for narration text, visual type, and visual data
    - _Requirements: R4.4_
  - [x] 19.3 Implement `src/components/script/SceneReorder.tsx` — drag-and-drop scene reordering with add/remove scene controls
    - _Requirements: R4.5_
  - [x] 19.4 Implement `src/components/script/DiffView.tsx` — side-by-side diff view comparing two script versions
    - _Requirements: R4.6_
  - [x] 19.5 Implement `src/components/script/FinalizeButton.tsx` — explicit finalize action with confirmation dialog
    - _Requirements: R4.7_

- [x] 20. Audio timeline editor
  - [x] 20.1 Implement `src/components/audio/SRTTimeline.tsx` — visual timeline display with segments showing start/end times and narration text
    - _Requirements: R5.1, R5.9_
  - [x] 20.2 Implement `src/components/audio/SegmentEditor.tsx` — edit narration text and adjust start/end timing per segment
    - _Requirements: R5.2, R5.3_
  - [x] 20.3 Implement `src/components/audio/VoiceParamControls.tsx` — sliders for speed, pitch, emphasis per segment
    - _Requirements: R5.5_
  - [x] 20.4 Implement `src/components/audio/AudioPreview.tsx` — per-segment synthesize trigger and audio playback
    - _Requirements: R5.6, R5.7_
  - [x] 20.5 Implement pause insertion control — insert silence between segments with configurable duration
    - _Requirements: R5.4_

- [x] 21. Visual scene editor
  - [x] 21.1 Implement `src/components/visual/SceneGrid.tsx` — scene grid with thumbnail previews and status indicators
    - _Requirements: R6.1_
  - [x] 21.2 Implement `src/components/visual/FootageSearch.tsx` — Pexels search interface with multiple footage options per scene
    - _Requirements: R6.2, R6.3_
  - [x] 21.3 Implement `src/components/visual/VisualTypeEditor.tsx` — change visual type, edit text overlay content, position, and style
    - _Requirements: R6.4, R6.5, R6.6_
  - [x] 21.4 Implement single-scene render trigger with job status tracking and thumbnail refresh
    - _Requirements: R6.7, R6.8_
  - [x] 21.5 Implement `src/components/visual/TransitionControls.tsx` — transition effect selection and configuration between scenes
    - _Requirements: R6.9_

- [x] 22. Music mixer and render panel
  - [x] 22.1 Implement `src/components/music/MusicUpload.tsx` and `src/components/music/MixControls.tsx` — MP3/WAV upload, volume slider (0-100%), fade-in/fade-out duration controls
    - _Requirements: R7.1, R7.2, R7.3_
  - [x] 22.2 Implement `src/components/music/MixPreview.tsx` — audio mix preview playback
    - _Requirements: R7.5_
  - [x] 22.3 Implement `src/components/render/RenderSceneList.tsx` — scene list with drag-and-drop reorder and remove controls, thumbnail + audio previews
    - _Requirements: R8.1, R8.2, R8.3_
  - [x] 22.4 Implement `src/components/render/RenderProgress.tsx` — final render trigger with real-time progress bar (percentage + current operation via WebSocket)
    - _Requirements: R8.4, R8.5_
  - [x] 22.5 Implement `src/components/render/VideoPreview.tsx` — rendered video playback and download
    - _Requirements: R8.6, R8.7_

## Notes

- Python 3.13, tests in `tests/unit/` and `tests/integration/`
- Frontend uses Node 20+, TypeScript strict mode
- Existing 220+ tests must continue passing after all changes
- Backend runs on port 8000, frontend dev server on port 5173 with proxy
- All existing pipeline modules (research_agent, script_generator, voice_synthesizer, asset_orchestrator) are consumed as-is — no modifications
- SQLite database at `.data/studio.db`, artifacts at `.data/artifacts/`
