-- Initial schema for Video Production Studio

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT    PRIMARY KEY,
    title           TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'DRAFT',
    current_stage   TEXT    NOT NULL DEFAULT 'RESEARCH',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT    PRIMARY KEY,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    job_type        TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'PENDING',
    input_json      TEXT,
    output_json     TEXT,
    error           TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    job_id          TEXT    REFERENCES jobs(id),
    artifact_type   TEXT    NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    file_path       TEXT    NOT NULL,
    metadata_json   TEXT,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id              TEXT    PRIMARY KEY,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           TEXT    NOT NULL,
    source          TEXT    NOT NULL,
    score           REAL    DEFAULT 0.0,
    keywords_json   TEXT,
    status          TEXT    NOT NULL DEFAULT 'PENDING',
    metadata_json   TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS script_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    topic_id        TEXT    NOT NULL REFERENCES topics(id),
    version         INTEGER NOT NULL,
    title           TEXT    NOT NULL,
    script_json     TEXT    NOT NULL,
    is_finalized    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    script_version_id INTEGER NOT NULL REFERENCES script_versions(id),
    scene_number    INTEGER NOT NULL,
    start_time      TEXT    NOT NULL,
    end_time        TEXT    NOT NULL,
    narration_text  TEXT    NOT NULL,
    voice_params_json TEXT,
    audio_file_path TEXT,
    status          TEXT    NOT NULL DEFAULT 'PENDING',
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_number    INTEGER NOT NULL,
    visual_type     TEXT    NOT NULL,
    visual_data_json TEXT   NOT NULL,
    stock_video_path TEXT,
    rendered_path   TEXT,
    thumbnail_path  TEXT,
    status          TEXT    NOT NULL DEFAULT 'PENDING',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_topics_project ON topics(project_id);
CREATE INDEX IF NOT EXISTS idx_script_versions_project ON script_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_script_versions_topic ON script_versions(topic_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_project ON audio_segments(project_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_script ON audio_segments(script_version_id);
CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id);
