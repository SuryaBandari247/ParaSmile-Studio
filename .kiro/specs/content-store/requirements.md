# Requirements Document

## Introduction

The Content Store is a local SQLite-backed persistence layer for the Faceless Technical Media Engine pipeline. It captures pipeline artifacts (scripts, search sessions, topic selections) so the user can browse production history, correlate past work by date or category, and avoid duplicating effort. The module uses only the Python standard library (`sqlite3`) and has zero dependency on Streamlit, keeping it testable in isolation.

## Glossary

- **Content_Store**: The Python module (`content_store/`) that owns the SQLite database connection, schema, and query helpers.
- **Pipeline_UI**: The Streamlit application (`pipeline_ui/`) that drives the five-step video production workflow.
- **VideoScript**: A dataclass (`script_generator.models.VideoScript`) representing a structured video script with title, scenes, generated_at, total_word_count, and metadata.
- **ScriptSerializer**: A class (`script_generator.serializer.ScriptSerializer`) that converts VideoScript objects to and from JSON strings.
- **Script_Record**: A row in the `scripts` table representing one saved VideoScript and its associated pipeline context.
- **Search_Session_Record**: A row in the `search_sessions` table representing one saved research search session.
- **Script_Link**: A row in the `script_links` table representing a directional relationship between two Script_Records.
- **DB_File**: The SQLite database file stored at `.data/content_store.db` relative to the project root.

## Requirements

### Requirement 1: Database Initialization

**User Story:** As a developer, I want the Content Store to create and configure the SQLite database automatically, so that no manual setup is needed.

#### Acceptance Criteria

1. WHEN the Content_Store is instantiated for the first time, THE Content_Store SHALL create the DB_File at the configured path, including any missing parent directories.
2. WHEN the Content_Store opens a database connection, THE Content_Store SHALL enable WAL journal mode for safe concurrent reads.
3. WHEN the Content_Store opens a database connection, THE Content_Store SHALL enable foreign key enforcement.
4. THE Content_Store SHALL create the `scripts` table, the `search_sessions` table, and the `script_links` table if they do not already exist.
5. WHEN the DB_File already exists with the correct schema, THE Content_Store SHALL open the existing database without data loss.

### Requirement 2: Scripts Table Schema

**User Story:** As a content producer, I want each converted VideoScript saved with its full context, so that I can review past productions in detail.

#### Acceptance Criteria

1. THE Content_Store SHALL store each Script_Record with the following columns: `id` (integer primary key, auto-increment), `title` (text, not null), `raw_script` (text, not null), `video_script_json` (text, not null), `selected_topic_json` (text), `documents_used` (integer, not null, default 0), `created_at` (text, not null, ISO 8601 UTC), `word_count` (integer, not null), `scene_count` (integer, not null).
2. THE Content_Store SHALL store `video_script_json` as the JSON string produced by ScriptSerializer.
3. THE Content_Store SHALL store `selected_topic_json` as a JSON string of the selected topic dictionary.
4. THE Content_Store SHALL store `created_at` as an ISO 8601 UTC timestamp string.

### Requirement 3: Search Sessions Table Schema

**User Story:** As a content producer, I want each research search session saved, so that I can see what topics were available when I made past decisions.

#### Acceptance Criteria

1. THE Content_Store SHALL store each Search_Session_Record with the following columns: `id` (integer primary key, auto-increment), `search_results_json` (text, not null), `query_date` (text, not null, ISO 8601 UTC), `topics_found` (integer, not null).
2. THE Content_Store SHALL store `search_results_json` as a JSON string of the full search results dictionary.
3. THE Content_Store SHALL store `query_date` as an ISO 8601 UTC timestamp string.

### Requirement 4: Save Script Record

**User Story:** As a content producer, I want the pipeline to save my converted script automatically, so that I never lose work.

#### Acceptance Criteria

1. WHEN the `save_script` method is called with a VideoScript, raw script text, selected topic dictionary, and document count, THE Content_Store SHALL insert a new Script_Record into the `scripts` table.
2. WHEN the `save_script` method is called, THE Content_Store SHALL serialize the VideoScript using ScriptSerializer and store the result in `video_script_json`.
3. WHEN the `save_script` method is called, THE Content_Store SHALL compute `scene_count` from the number of scenes in the VideoScript.
4. WHEN the `save_script` method is called, THE Content_Store SHALL set `created_at` to the current UTC time.
5. WHEN the `save_script` method succeeds, THE Content_Store SHALL return the integer `id` of the inserted row.
6. IF the database write fails, THEN THE Content_Store SHALL raise a `ContentStoreError` with a descriptive message.

### Requirement 5: Save Search Session Record

**User Story:** As a content producer, I want each search session saved, so that I can trace which research led to which scripts.

#### Acceptance Criteria

1. WHEN the `save_search_session` method is called with a search results dictionary, THE Content_Store SHALL insert a new Search_Session_Record into the `search_sessions` table.
2. WHEN the `save_search_session` method is called, THE Content_Store SHALL compute `topics_found` from the length of the topics list inside the search results dictionary.
3. WHEN the `save_search_session` method is called, THE Content_Store SHALL set `query_date` to the current UTC time.
4. WHEN the `save_search_session` method succeeds, THE Content_Store SHALL return the integer `id` of the inserted row.
5. IF the database write fails, THEN THE Content_Store SHALL raise a `ContentStoreError` with a descriptive message.

### Requirement 6: Query Script Records

**User Story:** As a content producer, I want to search and filter my past scripts, so that I can correlate previous work and avoid duplication.

#### Acceptance Criteria

1. WHEN `list_scripts` is called with no filters, THE Content_Store SHALL return all Script_Records ordered by `created_at` descending.
2. WHEN `list_scripts` is called with a `category` filter, THE Content_Store SHALL return only Script_Records whose `selected_topic_json` contains a matching `category` value.
3. WHEN `list_scripts` is called with a `keyword` filter, THE Content_Store SHALL return only Script_Records whose `title` or `raw_script` contains the keyword (case-insensitive).
4. WHEN `list_scripts` is called with `start_date` and `end_date` filters, THE Content_Store SHALL return only Script_Records whose `created_at` falls within the inclusive date range.
5. THE Content_Store SHALL return query results as a list of dictionaries, each containing all Script_Record columns.
6. WHEN `get_script` is called with a valid `id`, THE Content_Store SHALL return the single matching Script_Record as a dictionary.
7. IF `get_script` is called with an `id` that does not exist, THEN THE Content_Store SHALL return None.

### Requirement 7: Query Search Session Records

**User Story:** As a content producer, I want to browse past search sessions, so that I can see what research I did and when.

#### Acceptance Criteria

1. WHEN `list_search_sessions` is called, THE Content_Store SHALL return all Search_Session_Records ordered by `query_date` descending.
2. WHEN `get_search_session` is called with a valid `id`, THE Content_Store SHALL return the single matching Search_Session_Record as a dictionary.
3. IF `get_search_session` is called with an `id` that does not exist, THEN THE Content_Store SHALL return None.

### Requirement 8: Auto-Save on Conversion

**User Story:** As a content producer, I want my script saved automatically when conversion completes, so that I do not need to remember to save manually.

#### Acceptance Criteria

1. WHEN the Pipeline_UI completes a successful conversion in the convert panel, THE Pipeline_UI SHALL call `save_script` on the Content_Store with the current VideoScript, raw script, selected topic, and document count from session state.
2. WHEN the auto-save succeeds, THE Pipeline_UI SHALL display a confirmation message including the Script_Record `id`.
3. IF the auto-save fails, THEN THE Pipeline_UI SHALL display a warning message and allow the user to continue the pipeline without blocking.
4. THE Pipeline_UI SHALL save the search session via `save_search_session` when search results are first obtained in the search panel, so that the research context is captured independently of conversion.

### Requirement 9: History View

**User Story:** As a content producer, I want a history view in the UI to browse past scripts and search sessions, so that I can review and correlate previous work.

#### Acceptance Criteria

1. THE Pipeline_UI SHALL provide a "History" sidebar section accessible from any pipeline step.
2. WHEN the user opens the History view, THE Pipeline_UI SHALL display a list of past Script_Records showing title, created_at, word_count, and scene_count.
3. WHEN the user selects a Script_Record from the history list, THE Pipeline_UI SHALL display the full script details including raw script, VideoScript JSON, and selected topic.
4. THE Pipeline_UI SHALL provide filter controls for keyword search, date range, and topic category in the History view.
5. WHEN the user opens the History view, THE Pipeline_UI SHALL display a list of past Search_Session_Records showing query_date and topics_found.

### Requirement 10: Module Isolation

**User Story:** As a developer, I want the Content Store module to have no Streamlit dependency, so that it can be tested and reused independently.

#### Acceptance Criteria

1. THE Content_Store module SHALL import only Python standard library modules.
2. THE Content_Store module SHALL accept the database file path as a constructor parameter with a default of `.data/content_store.db`.
3. THE Content_Store module SHALL expose a `close` method that closes the database connection.
4. THE Content_Store module SHALL support use as a context manager (`with` statement) for automatic connection cleanup.

### Requirement 11: Serialization Round-Trip Integrity

**User Story:** As a developer, I want to verify that scripts stored and retrieved from the database maintain data integrity, so that no information is lost in persistence.

#### Acceptance Criteria

1. FOR ALL valid VideoScript objects, saving a Script_Record and then retrieving the `video_script_json` and deserializing it via ScriptSerializer SHALL produce a VideoScript equivalent to the original.
2. FOR ALL valid search results dictionaries, saving a Search_Session_Record and then retrieving the `search_results_json` and deserializing it via `json.loads` SHALL produce a dictionary equivalent to the original.


### Requirement 12: Script Links Table Schema

**User Story:** As a content producer, I want a dedicated table for cross-referencing scripts, so that I can track how my videos relate to each other.

#### Acceptance Criteria

1. THE Content_Store SHALL store each Script_Link with the following columns: `id` (integer primary key, auto-increment), `source_script_id` (integer, not null, foreign key referencing `scripts.id`), `target_script_id` (integer, not null, foreign key referencing `scripts.id`), `link_type` (text, not null), `note` (text, nullable), `created_at` (text, not null, ISO 8601 UTC).
2. THE Content_Store SHALL enforce foreign key constraints on `source_script_id` and `target_script_id` referencing the `scripts` table `id` column.
3. THE Content_Store SHALL enforce a unique constraint on the combination of (`source_script_id`, `target_script_id`, `link_type`) to prevent duplicate links.
4. THE Content_Store SHALL accept `link_type` values including "continuation", "deep_dive", "see_also", and "related".

### Requirement 13: Link Scripts

**User Story:** As a content producer, I want to create explicit links between scripts, so that I can record when one video references another.

#### Acceptance Criteria

1. WHEN `link_scripts` is called with a valid `source_id`, `target_id`, `link_type`, and optional `note`, THE Content_Store SHALL insert a new Script_Link into the `script_links` table.
2. WHEN `link_scripts` is called, THE Content_Store SHALL validate that both `source_id` and `target_id` exist in the `scripts` table before inserting.
3. IF `link_scripts` is called with a `source_id` or `target_id` that does not exist in the `scripts` table, THEN THE Content_Store SHALL raise a `ContentStoreError` with a message identifying the missing script.
4. IF `link_scripts` is called with a (`source_id`, `target_id`, `link_type`) combination that already exists, THEN THE Content_Store SHALL raise a `ContentStoreError` indicating the duplicate link.
5. WHEN `link_scripts` succeeds, THE Content_Store SHALL return the integer `id` of the inserted Script_Link.
6. WHEN `link_scripts` is called, THE Content_Store SHALL set `created_at` to the current UTC time.

### Requirement 14: Find Related Scripts

**User Story:** As a content producer, I want to discover scripts related to a given script through explicit links, shared categories, and overlapping title keywords, so that I can build cross-references into my videos.

#### Acceptance Criteria

1. WHEN `find_related_scripts` is called with a valid `script_id`, THE Content_Store SHALL return scripts related through explicit links in both directions (where the script is either `source_script_id` or `target_script_id`).
2. WHEN `find_related_scripts` is called, THE Content_Store SHALL return scripts that share the same topic category as the given script, detected by comparing the `category` field inside `selected_topic_json`.
3. WHEN `find_related_scripts` is called, THE Content_Store SHALL return scripts that have overlapping keywords in the `title` column compared to the given script title.
4. THE Content_Store SHALL return results as a list of dictionaries, each containing Script_Record summary fields (`id`, `title`, `created_at`, `word_count`, `scene_count`), a `relationship_type` field with value "linked", "same_category", or "keyword_overlap", and for "linked" results, additional `link_type` and `note` fields.
5. WHEN a script appears in multiple relationship types, THE Content_Store SHALL include the script once per distinct relationship type.
6. WHEN `get_script_links` is called with a valid `script_id`, THE Content_Store SHALL return only the explicit Script_Link records for that script (both directions) as a list of dictionaries.
7. IF `find_related_scripts` or `get_script_links` is called with a `script_id` that does not exist, THEN THE Content_Store SHALL return an empty list.

### Requirement 15: Cross-Reference in History View

**User Story:** As a content producer, I want to see related scripts when viewing a script in the History sidebar, so that I can quickly navigate between connected videos and create new links.

#### Acceptance Criteria

1. WHEN the user selects a Script_Record in the History view, THE Pipeline_UI SHALL display a "Related Scripts" section below the script details.
2. THE Pipeline_UI SHALL display explicit links in the "Related Scripts" section with the link type, target script title, and note.
3. THE Pipeline_UI SHALL display auto-detected relationships (same category, keyword overlap) in the "Related Scripts" section with the relationship type and target script title.
4. THE Pipeline_UI SHALL provide a control in the History view to create a new link between the currently viewed script and another script, allowing the user to select a target script, choose a link type, and add an optional note.
5. WHEN the user creates a new link from the History view, THE Pipeline_UI SHALL call `link_scripts` on the Content_Store and refresh the "Related Scripts" section.
6. IF creating a new link fails, THEN THE Pipeline_UI SHALL display a warning message with the error details without blocking the History view.
