# Implementation Plan: Pipeline UI

## Overview

Build the `pipeline_ui` Streamlit web application that provides a human-in-the-loop interface for the content production pipeline. Implementation proceeds bottom-up: dependencies → document parser → session state/navigation → step panels → entry point wiring. All new business logic is testable in isolation from Streamlit.

## Tasks

- [x] 1. Add dependencies and set up package structure
  - [x] 1.1 Add new dependencies to `requirements.txt`
    - Add `streamlit>=1.30.0`, `pypdf>=3.17.0`, `openpyxl>=3.1.2`, `python-docx>=1.1.0`
    - _Requirements: 1.1_

  - [x] 1.2 Create `pipeline_ui/` package with module files
    - Create `pipeline_ui/__init__.py`
    - Create `pipeline_ui/app.py` (empty placeholder)
    - Create `pipeline_ui/navigation.py` (empty placeholder)
    - Create `pipeline_ui/session_state.py` (empty placeholder)
    - Create `pipeline_ui/document_parser.py` (empty placeholder)
    - Create `pipeline_ui/panels/__init__.py`
    - Create `pipeline_ui/panels/search_panel.py` (empty placeholder)
    - Create `pipeline_ui/panels/select_topic_panel.py` (empty placeholder)
    - Create `pipeline_ui/panels/script_input_panel.py` (empty placeholder)
    - Create `pipeline_ui/panels/convert_panel.py` (empty placeholder)
    - Create `pipeline_ui/panels/review_panel.py` (empty placeholder)
    - _Requirements: 1.1, 1.2_

- [ ] 2. Implement document parser
  - [x] 2.1 Implement `pipeline_ui/document_parser.py`
    - Define `SUPPORTED_EXTENSIONS` set: `.pdf`, `.xlsx`, `.csv`, `.txt`, `.md`, `.docx`
    - Implement `ParsedDocument` dataclass with `filename`, `text`, `char_count`, `success`, `error`
    - Implement `parse_file(filename, content_bytes)` dispatching to format-specific extractors
    - Implement `_extract_pdf` using `pypdf`, extracting text from all pages
    - Implement `_extract_xlsx` using `openpyxl`, reading all sheets, rows as comma-separated lines
    - Implement `_extract_csv` using stdlib `csv`, reading content as plain text
    - Implement `_extract_txt` decoding bytes as UTF-8
    - Implement `_extract_docx` using `python-docx`, extracting all paragraph text
    - Return `ParsedDocument(success=False, error=...)` for unsupported extensions or extraction failures
    - Implement `parse_files(files)` calling `parse_file` for each, returning all results (no short-circuit)
    - Implement `concatenate_extracted_text(documents)` wrapping each successful doc in boundary markers
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12_

  - [x] 2.2 Write unit tests for document parser (`tests/unit/test_document_parser.py`)
    - Test `parse_file` with a valid UTF-8 `.txt` file
    - Test `parse_file` with a valid `.csv` file
    - Test `parse_file` with a valid `.md` file
    - Test `parse_file` with an unsupported extension returns `success=False` with error message
    - Test `parse_file` with a 0-byte file
    - Test `parse_files` returns one result per input file, including failures
    - Test `concatenate_extracted_text` with multiple documents produces correct boundary markers
    - Test `concatenate_extracted_text` with an empty list returns empty string
    - Test `_extract_pdf` with a simple PDF (create in-memory with `pypdf`)
    - Test `_extract_xlsx` with a simple workbook (create in-memory with `openpyxl`)
    - Test `_extract_docx` with a simple document (create in-memory with `python-docx`)
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12_

  - [ ]* 2.3 Write property test: plain text round-trip (P5)
    - **Property 5: Plain text file round-trip**
    - **Validates: Requirements 6.6, 6.7**

  - [ ]* 2.4 Write property test: unsupported format rejection (P9)
    - **Property 9: Unsupported format rejection**
    - **Validates: Requirements 6.9**

  - [ ]* 2.5 Write property test: batch parse resilience (P10)
    - **Property 10: Batch parse resilience**
    - **Validates: Requirements 6.10**

  - [ ]* 2.6 Write property test: document concatenation boundary markers (P11)
    - **Property 11: Document concatenation boundary markers**
    - **Validates: Requirements 6.12, 7.1**

- [ ] 3. Implement session state and navigation
  - [x] 3.1 Implement `pipeline_ui/navigation.py`
    - Define `PipelineStep` IntEnum: SEARCH=0, SELECT_TOPIC=1, SCRIPT_INPUT=2, CONVERT=3, REVIEW=4
    - Define `STEP_LABELS` list
    - Implement `can_advance(current_step, pipeline_data)` checking step completion criteria:
      - SEARCH: `search_results` is not None
      - SELECT_TOPIC: `selected_topic` is not None
      - SCRIPT_INPUT: `raw_script` is non-empty
      - CONVERT: `video_script` is not None
    - Implement `go_to_step(step)` allowing navigation only to steps <= max_completed_step + 1
    - Implement `render_progress_bar()` showing current/completed steps using Streamlit columns
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Implement `pipeline_ui/session_state.py`
    - Implement `PipelineData` dataclass with all fields from design (current_step, max_completed_step, search_results, selected_topic, raw_script, parsed_documents, video_script, conversion_metadata)
    - Implement `init_session_state()` creating default `PipelineData` in `st.session_state` if absent
    - Implement `get_pipeline()` returning current `PipelineData`
    - Implement `clear_session_state()` resetting to default `PipelineData`
    - _Requirements: 2.6, 10.1, 10.2, 10.3_

  - [x] 3.3 Write unit tests for navigation and session state (`tests/unit/test_navigation.py`, `tests/unit/test_session_state.py`)
    - Test `can_advance` returns False for each step when criteria not met
    - Test `can_advance` returns True for each step when criteria met
    - Test `go_to_step` succeeds for completed steps, fails for uncompleted
    - Test `clear_session_state` produces default `PipelineData`
    - Test `init_session_state` is idempotent (does not overwrite existing state)
    - _Requirements: 2.3, 2.5, 10.3_

  - [ ]* 3.4 Write property test: step completion gating (P4)
    - **Property 4: Step completion gating**
    - **Validates: Requirements 2.5, 5.3**

  - [ ]* 3.5 Write property test: session state reset (P13)
    - **Property 13: Session state reset**
    - **Validates: Requirements 10.3**

- [x] 4. Checkpoint — Ensure foundation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement step panels
  - [x] 5.1 Implement `pipeline_ui/panels/search_panel.py`
    - Render "Search for Trends" button that invokes `ResearchAgent().get_trending_topics()`
    - Display spinner with status message while agent executes
    - On success: store results in `pipeline_data.search_results`, render Topic Cards (title, hook, context_type, category, source trend count)
    - On error: display error banner, suggest recovery action, offer retry
    - Render "Regenerate Pitches" button to re-invoke with same raw trends
    - Update `max_completed_step` on success
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 9.1, 9.3_

  - [x] 5.2 Implement `pipeline_ui/panels/select_topic_panel.py`
    - Display Story_Pitch_Board as selectable Topic Cards using `st.radio` or card layout
    - On selection: highlight card, show full source trend details
    - Provide "Confirm Selection" button that stores `selected_topic` and advances to Script Input
    - Allow changing selection before confirming
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.3 Implement `pipeline_ui/panels/script_input_panel.py`
    - Display selected topic title and hook as context header
    - Render multi-line `st.text_area` for raw script input
    - Display character count below text area
    - Render `st.file_uploader` accepting multiple files (PDF, XLSX, CSV, TXT, MD, DOCX)
    - On file upload: call `document_parser.parse_files()`, display parsed doc list with char counts
    - Display warnings for any failed parses
    - Store `raw_script` and `parsed_documents` in pipeline state
    - Prevent advancement when text area is empty
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.9, 6.10, 6.11_

  - [x] 5.4 Implement `pipeline_ui/panels/convert_panel.py`
    - Render "Convert to VideoScript" button
    - On click: concatenate raw script + extracted text using `concatenate_extracted_text()`
    - Invoke `ScriptConverter().convert(concatenated_text)` with spinner
    - On success: store `video_script` in pipeline state, advance to Review
    - On `ParseError`/`ValidationError`: display error details, suggest editing script, offer retry
    - On `AuthenticationError`: display configuration error banner
    - Display model name and token counts after conversion
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 9.2_

  - [x] 5.5 Implement `pipeline_ui/panels/review_panel.py`
    - Display VideoScript title, total word count, generation timestamp
    - Render each Scene_Block in an expander: scene number, narration text, visual instruction type/title/data
    - Provide "Download VideoScript JSON" button using `st.download_button`
    - Provide "Back to Script" button navigating to Script Input step
    - Render collapsible "Raw JSON" section with `st.code`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6. Implement app entry point and error handling
  - [x] 6.1 Implement `pipeline_ui/app.py`
    - Set Streamlit page config (title="Pipeline UI", layout="wide")
    - Load `.env` via `python-dotenv`
    - Implement `validate_env_vars(var_names)` returning list of missing variable names
    - Display error banner and `st.stop()` if required env vars missing
    - Call `init_session_state()`, `render_progress_bar()`, delegate to current panel
    - Render "Start New Pipeline" button with `st.dialog` confirmation that calls `clear_session_state()`
    - Set up `logging.getLogger("pipeline_ui")` for error logging with step context
    - Classify errors as configuration (AuthenticationError, missing env) vs recoverable (ParseError, ValidationError, NetworkError, QuotaExceededError)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.1, 9.2, 9.3, 9.4, 10.3, 10.4_

  - [ ]* 6.2 Write property test: environment variable validation (P1)
    - **Property 1: Environment variable validation**
    - **Validates: Requirements 1.4, 1.5**

  - [ ]* 6.3 Write property test: error classification correctness (P12)
    - **Property 12: Error classification correctness**
    - **Validates: Requirements 9.2**

- [x] 7. Wire package exports and integration
  - [x] 7.1 Update `pipeline_ui/__init__.py` with public exports
    - Export `PipelineStep`, `PipelineData`, `ParsedDocument`
    - Export `init_session_state`, `clear_session_state`, `get_pipeline`
    - Export `parse_file`, `parse_files`, `concatenate_extracted_text`
    - _Requirements: N/A (package API)_

  - [x] 7.2 Write integration-level unit tests (`tests/unit/test_pipeline_ui_integration.py`)
    - Test full panel dispatch: each `PipelineStep` value routes to the correct panel render function
    - Test env var validation with all present, one missing, all missing
    - Test error classification for each known exception type
    - _Requirements: 1.4, 1.5, 2.1, 9.2_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property tests — skip for faster MVP
- All Streamlit widget interactions are tested indirectly through logic functions; panels themselves are thin UI wrappers
- Follows the same module patterns as `research_agent/` and `script_generator/` (config, exceptions, logger)
- Python 3.13, tests in `tests/unit/`
- Existing 220 tests must continue passing after all changes
