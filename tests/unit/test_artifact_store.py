"""Unit tests for ArtifactStore service."""

import os
import tempfile

import pytest

from studio_api.database import get_connection, run_migrations
from studio_api.models.project import ProjectCreate
from studio_api.services.artifact_store import ArtifactStore
from studio_api.services.project_service import ProjectService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_id(db):
    svc = ProjectService(db)
    p = svc.create(ProjectCreate(title="Test Project"))
    return p.id


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def store(db, tmp_dir):
    return ArtifactStore(db, base_dir=tmp_dir)


class TestStore:
    def test_store_creates_file(self, store, project_id, tmp_dir):
        result = store.store(project_id, "script_json", "script.json", b'{"scenes": []}')
        assert result["version"] == 1
        assert result["artifact_type"] == "script_json"
        abs_path = os.path.join(tmp_dir, result["file_path"])
        assert os.path.exists(abs_path)
        with open(abs_path, "rb") as f:
            assert f.read() == b'{"scenes": []}'

    def test_store_increments_version(self, store, project_id):
        r1 = store.store(project_id, "script_json", "script.json", b"v1")
        r2 = store.store(project_id, "script_json", "script.json", b"v2")
        assert r1["version"] == 1
        assert r2["version"] == 2

    def test_store_different_types_independent_versions(self, store, project_id):
        r1 = store.store(project_id, "script_json", "script.json", b"data")
        r2 = store.store(project_id, "audio_segment", "seg.mp3", b"audio")
        assert r1["version"] == 1
        assert r2["version"] == 1

    def test_store_with_metadata(self, store, project_id):
        result = store.store(
            project_id, "scene_render", "scene.mp4", b"video",
            metadata={"scene_number": 1, "duration": 5.2},
        )
        assert result["metadata"] == {"scene_number": 1, "duration": 5.2}

    def test_store_with_job_id(self, db, store, project_id):
        from studio_api.services.job_runner import JobRunner
        runner = JobRunner(db)
        job = runner.create_job(project_id, "research_youtube")
        result = store.store(
            project_id, "script_json", "script.json", b"data",
            job_id=job.id,
        )
        assert result["job_id"] == job.id

    def test_store_preserves_old_versions(self, store, project_id, tmp_dir):
        r1 = store.store(project_id, "script_json", "script.json", b"v1")
        r2 = store.store(project_id, "script_json", "script.json", b"v2")
        # Both files exist
        assert os.path.exists(os.path.join(tmp_dir, r1["file_path"]))
        assert os.path.exists(os.path.join(tmp_dir, r2["file_path"]))
        # Contents differ
        assert store.read(r1["file_path"]) == b"v1"
        assert store.read(r2["file_path"]) == b"v2"


class TestGet:
    def test_get_existing(self, store, project_id):
        result = store.store(project_id, "script_json", "script.json", b"data")
        fetched = store.get(result["id"])
        assert fetched is not None
        assert fetched["id"] == result["id"]
        assert fetched["version"] == 1

    def test_get_nonexistent(self, store):
        assert store.get(9999) is None


class TestListArtifacts:
    def test_list_empty(self, store, project_id):
        assert store.list_artifacts(project_id) == []

    def test_list_all_types(self, store, project_id):
        store.store(project_id, "script_json", "s.json", b"a")
        store.store(project_id, "audio_segment", "a.mp3", b"b")
        artifacts = store.list_artifacts(project_id)
        assert len(artifacts) == 2

    def test_list_filtered_by_type(self, store, project_id):
        store.store(project_id, "script_json", "s.json", b"a")
        store.store(project_id, "audio_segment", "a.mp3", b"b")
        scripts = store.list_artifacts(project_id, artifact_type="script_json")
        assert len(scripts) == 1
        assert scripts[0]["artifact_type"] == "script_json"

    def test_list_versions_ordered_desc(self, store, project_id):
        store.store(project_id, "script_json", "s.json", b"v1")
        store.store(project_id, "script_json", "s.json", b"v2")
        scripts = store.list_artifacts(project_id, artifact_type="script_json")
        assert scripts[0]["version"] == 2
        assert scripts[1]["version"] == 1


class TestGetLatest:
    def test_get_latest_returns_highest_version(self, store, project_id):
        store.store(project_id, "script_json", "s.json", b"v1")
        store.store(project_id, "script_json", "s.json", b"v2")
        latest = store.get_latest(project_id, "script_json")
        assert latest["version"] == 2

    def test_get_latest_no_artifacts(self, store, project_id):
        assert store.get_latest(project_id, "script_json") is None


class TestRead:
    def test_read_existing(self, store, project_id):
        result = store.store(project_id, "script_json", "s.json", b"content")
        assert store.read(result["file_path"]) == b"content"

    def test_read_nonexistent(self, store):
        assert store.read("nonexistent/path/file.txt") is None


class TestGetAbsolutePath:
    def test_resolves_path(self, store, tmp_dir):
        abs_path = store.get_absolute_path("proj/type/v1/file.txt")
        assert abs_path == os.path.join(tmp_dir, "proj/type/v1/file.txt")
