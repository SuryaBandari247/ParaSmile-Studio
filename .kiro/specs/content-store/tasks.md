# Implementation Plan: Content Store

## Overview

Implement a local SQLite-backed persistence layer (`content_store/`) for pipeline artifacts, then integrate auto-save and history browsing into the existing Pipeline UI. The module uses only Python stdlib (`sqlite3`), keeping it testable in isolation. Tasks proceed from core package structure through CRUD operations, linking, and finally UI integration.

## Tasks

- [x] 1. Create package structure and exception module
  - [x] 1.1 Create `content_store/__init__.py` with `ContentStore` and `ContentStoreError` exports
    - Export `ContentStore` from `content_store.store` and `ContentStoreError` from `content_store.exceptions`
    - _Requirements: 10.1_
  - [x] 1.2 Create `content_store/exceptions.py` with `ContentStoreError` class
    - Single exception class inheriting from `Exception`
    - _Requirements: 4.6, 5.5, 13.3, 13.4_

- [x] 2. Implement ContentStore — initialization, close, context manager, schema
  - [x] 2.1 Implement `ContentStore.__init__` — create DB file, parent dirs, WAL mode, foreign keys, schema
    - Accept `db_path` parameter with default `.data/content_store.db`
    - Create parent directories with `os.makedirs`
    - Enable WAL journal mode and foreign key enforcement via PRAGMAs
    - Create `scripts`, `search_sessions`, and `script_links` tables if not exist
    - Set `conn.row_factory = sqlite3.Row`
    - Raise `ContentStoreError` on failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.2_
  - [x] 2.2 Implement `close()` and context manager (`__enter__`, `__exit__`)
    - `close()` closes the sqlite3 connection
    - `__enter__` returns self, `__exit__` calls `close()`
    - _Requirements: 10.3, 10.4_

- [x] 3. Implement save_script and query methods
  - [x] 3.1 Implement `save_script` method
    - Serialize `VideoScript` via `ScriptSerializer.serialize()`
    - Serialize `selected_topic` via `json.dumps()` (or None)
    - Compute `scene_count` from `len(video_script.scenes)`
    - Use `video_script.total_word_count` for `word_count`
    - Set `created_at` to current UTC time as ISO 8601 string
    - INSERT into `scripts` table, return `cursor.lastrowid`
    - Raise `ContentStoreError` on failure
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 2.1, 2.2, 2.3, 2.4_
  - [x] 3.2 Implement `get_script` and `list_scripts` methods
    - `get_script(script_id)` returns dict or None
    - `list_scripts` supports `category`, `keyword`, `start_date`, `end_date` filters
    - Category filter: JSON extract or LIKE on `selected_topic_json` for `"category"` value
    - Keyword filter: case-insensitive LIKE on `title` or `raw_script`
    - Date range filter: inclusive range on `created_at`
    - Results ordered by `created_at` DESC, returned as list of dicts
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 4. Write unit tests for script CRUD
  - [x] 4.1 Write unit tests in `tests/unit/test_content_store.py` for database initialization
    - Test DB file creation with parent directories
    - Test WAL mode is enabled
    - Test foreign keys are enabled
    - Test tables exist after init
    - Test re-opening existing DB preserves data
    - Test context manager opens and closes connection
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.3, 10.4_
  - [x] 4.2 Write unit tests for `save_script`, `get_script`, `list_scripts`
    - Test save returns integer id
    - Test get retrieves saved script with all fields
    - Test get returns None for non-existent id
    - Test list returns all scripts in descending created_at order
    - Test category filter
    - Test keyword filter (case-insensitive)
    - Test date range filter
    - Test save raises ContentStoreError on closed connection
    - _Requirements: 4.1–4.6, 6.1–6.7_
  - [ ]* 4.3 Write property test for script serialization round-trip
    - **Property 1: Script serialization round-trip**
    - **Validates: Requirements 11.1, 2.2, 4.2, 4.5, 6.6**
  - [ ]* 4.4 Write property test for computed fields correctness
    - **Property 3: Computed fields are correct**
    - **Validates: Requirements 4.3, 5.2**
  - [ ]* 4.5 Write property test for ISO 8601 timestamps
    - **Property 4: All stored timestamps are valid ISO 8601 UTC**
    - **Validates: Requirements 2.4, 3.3, 4.4, 5.3, 13.6**
  - [ ]* 4.6 Write property test for descending chronological order
    - **Property 5: List queries return results in descending chronological order**
    - **Validates: Requirements 6.1, 7.1**
  - [ ]* 4.7 Write property test for category filter
    - **Property 6: Category filter returns only matching scripts**
    - **Validates: Requirements 6.2**
  - [ ]* 4.8 Write property test for keyword filter
    - **Property 7: Keyword filter returns only matching scripts**
    - **Validates: Requirements 6.3**
  - [ ]* 4.9 Write property test for date range filter
    - **Property 8: Date range filter returns only scripts within range**
    - **Validates: Requirements 6.4**

- [x] 5. Implement search session CRUD
  - [x] 5.1 Implement `save_search_session` method
    - Serialize `search_results` via `json.dumps()`
    - Compute `topics_found` from `len(search_results.get("topics", []))`
    - Set `query_date` to current UTC time as ISO 8601 string
    - INSERT into `search_sessions` table, return `cursor.lastrowid`
    - Raise `ContentStoreError` on failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 3.1, 3.2, 3.3_
  - [x] 5.2 Implement `get_search_session` and `list_search_sessions` methods
    - `get_search_session(session_id)` returns dict or None
    - `list_search_sessions()` returns all records ordered by `query_date` DESC
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ]* 5.3 Write property test for search session round-trip
    - **Property 2: Search session round-trip**
    - **Validates: Requirements 11.2, 3.2, 5.4, 7.2**

- [x] 6. Implement script links — link_scripts, get_script_links, find_related_scripts
  - [x] 6.1 Implement `link_scripts` method
    - Validate both `source_id` and `target_id` exist in `scripts` table
    - Raise `ContentStoreError` if either id is missing (identify which)
    - INSERT into `script_links` table with `link_type`, optional `note`, and UTC `created_at`
    - Raise `ContentStoreError` on duplicate (`source_id`, `target_id`, `link_type`) combination
    - Return `cursor.lastrowid`
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 12.1, 12.2, 12.3, 12.4_
  - [x] 6.2 Implement `get_script_links` method
    - Query `script_links` where script is source or target
    - Return list of dicts, or empty list if script_id does not exist
    - _Requirements: 14.6, 14.7_
  - [x] 6.3 Implement `find_related_scripts` method
    - Find explicitly linked scripts (both directions) — `relationship_type="linked"` with `link_type` and `note`
    - Find same-category scripts via `selected_topic_json` category comparison — `relationship_type="same_category"`
    - Find keyword-overlap scripts by comparing title words — `relationship_type="keyword_overlap"`
    - Include a script once per distinct relationship type
    - Return list of dicts with summary fields, or empty list if script_id does not exist
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.7_

- [x] 7. Write unit tests for search sessions and links
  - [x] 7.1 Write unit tests for `save_search_session`, `get_search_session`, `list_search_sessions`
    - Test save returns integer id
    - Test get retrieves saved session with all fields
    - Test get returns None for non-existent id
    - Test list returns all sessions in descending query_date order
    - Test save raises ContentStoreError on closed connection
    - _Requirements: 5.1–5.5, 7.1–7.3_
  - [x] 7.2 Write unit tests for `link_scripts`, `get_script_links`, `find_related_scripts`
    - Test link creation returns id
    - Test link with non-existent source raises ContentStoreError
    - Test link with non-existent target raises ContentStoreError
    - Test duplicate link raises ContentStoreError
    - Test accepted link_type values ("continuation", "deep_dive", "see_also", "related")
    - Test get_script_links returns links in both directions
    - Test get_script_links returns empty list for non-existent script
    - Test find_related_scripts returns linked, same_category, and keyword_overlap results
    - Test find_related_scripts includes script once per relationship type
    - Test find_related_scripts returns empty list for non-existent script
    - _Requirements: 12.1–12.4, 13.1–13.6, 14.1–14.7_
  - [ ]* 7.3 Write property test for bidirectional link discovery
    - **Property 9: Explicit links are discoverable in both directions**
    - **Validates: Requirements 14.1, 14.6**
  - [ ]* 7.4 Write property test for same-category discovery
    - **Property 10: Same-category scripts are discovered**
    - **Validates: Requirements 14.2**
  - [ ]* 7.5 Write property test for keyword-overlap discovery
    - **Property 11: Keyword-overlap scripts are discovered**
    - **Validates: Requirements 14.3**
  - [ ]* 7.6 Write property test for multiple relationship types
    - **Property 12: Scripts appearing in multiple relationship types are included once per type**
    - **Validates: Requirements 14.5**
  - [ ]* 7.7 Write property test for foreign key enforcement
    - **Property 13: Foreign key enforcement on script links**
    - **Validates: Requirements 12.2, 13.2, 13.3**
  - [ ]* 7.8 Write property test for unique constraint on links
    - **Property 14: Unique constraint on script links**
    - **Validates: Requirements 12.3, 13.4**

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Integrate auto-save into convert_panel.py
  - [x] 9.1 Add auto-save call in `convert_panel.py` after successful conversion
    - Import `ContentStore` from `content_store`
    - After `pipeline.video_script` is set, call `save_script` with `video_script`, `raw_script`, `selected_topic`, and `documents_used`
    - Display `st.success` with script id on success
    - Catch exceptions, log warning, display `st.warning`, do not block pipeline
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 10. Integrate auto-save into search_panel.py
  - [x] 10.1 Add auto-save call in `search_panel.py` after successful search
    - Import `ContentStore` from `content_store`
    - After `pipeline.search_results` is set, call `save_search_session` with the search results
    - Log success with session id
    - Catch exceptions, log warning, do not block pipeline
    - _Requirements: 8.4_

- [x] 11. Implement History sidebar in app.py
  - [x] 11.1 Add History sidebar section in `app.py`
    - Add `st.sidebar.divider()` and `st.sidebar.subheader("History")` after existing sidebar content
    - Display list of past Script_Records showing title, created_at, word_count, scene_count
    - Display list of past Search_Session_Records showing query_date and topics_found
    - Add filter controls for keyword search, date range, and topic category
    - _Requirements: 9.1, 9.2, 9.4, 9.5_
  - [x] 11.2 Implement script detail view and Related Scripts section
    - On script selection, display full details: raw script, VideoScript JSON, selected topic
    - Display "Related Scripts" section with explicit links (link type, title, note) and auto-detected relationships (same category, keyword overlap)
    - _Requirements: 9.3, 15.1, 15.2, 15.3_
  - [x] 11.3 Implement link creation controls in History view
    - Provide controls to select target script, choose link type, add optional note
    - Call `link_scripts` on submit and refresh Related Scripts section
    - Display `st.warning` on failure without blocking History view
    - _Requirements: 15.4, 15.5, 15.6_

- [ ] 12. Write integration tests for UI hooks
  - [ ]* 12.1 Write integration tests in `tests/unit/test_content_store_ui.py`
    - Test convert_panel auto-save calls `save_script` on successful conversion
    - Test convert_panel displays success message with script id
    - Test convert_panel handles save failure gracefully (warning, no block)
    - Test search_panel auto-save calls `save_search_session` on successful search
    - Test search_panel handles save failure gracefully
    - Test History sidebar renders script list and search session list
    - Test History sidebar filter controls work
    - Test Related Scripts section displays on script selection
    - Test link creation from History view
    - _Requirements: 8.1–8.4, 9.1–9.5, 15.1–15.6_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Hypothesis library)
- Unit tests validate specific examples and edge cases
- The content_store module imports only Python stdlib — no Streamlit dependency
