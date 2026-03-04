"""Unit tests for ScriptService and scripts router."""

import json

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.project import ProjectCreate
from studio_api.models.script import ScriptVersionCreate, ScriptVersionUpdate
from studio_api.models.topic import TopicCreate
from studio_api.services.project_service import ProjectService
from studio_api.services.script_service import ScriptService
from studio_api.services.topic_service import TopicService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_id(db):
    return ProjectService(db).create(ProjectCreate(title="Test")).id


@pytest.fixture
def topic_id(db, project_id):
    return TopicService(db).create(project_id, TopicCreate(title="AI")).id


@pytest.fixture
def service(db):
    return ScriptService(db)


SAMPLE_SCRIPT = {"title": "Test", "scenes": [{"scene_number": 1, "narration_text": "Hello world"}]}


class TestScriptServiceCreate:
    def test_create_first_version(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Draft 1", script_json=SAMPLE_SCRIPT
        ))
        assert sv.version == 1
        assert sv.title == "Draft 1"
        assert sv.is_finalized is False
        assert sv.script_json == SAMPLE_SCRIPT

    def test_create_increments_version(self, service, project_id, topic_id):
        sv1 = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V1", script_json=SAMPLE_SCRIPT
        ))
        sv2 = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V2", script_json=SAMPLE_SCRIPT
        ))
        assert sv1.version == 1
        assert sv2.version == 2


class TestScriptServiceGet:
    def test_get_existing(self, service, project_id, topic_id):
        created = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Test", script_json=SAMPLE_SCRIPT
        ))
        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent(self, service):
        assert service.get(9999) is None


class TestScriptServiceUpdate:
    def test_update_title(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Old", script_json=SAMPLE_SCRIPT
        ))
        updated = service.update(sv.id, ScriptVersionUpdate(title="New"))
        assert updated.title == "New"

    def test_update_script_json(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Test", script_json=SAMPLE_SCRIPT
        ))
        new_json = {"title": "Updated", "scenes": []}
        updated = service.update(sv.id, ScriptVersionUpdate(script_json=new_json))
        assert updated.script_json == new_json

    def test_update_finalized_raises(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Test", script_json=SAMPLE_SCRIPT
        ))
        service.finalize(sv.id)
        with pytest.raises(ValueError, match="finalized"):
            service.update(sv.id, ScriptVersionUpdate(title="Nope"))

    def test_update_nonexistent(self, service):
        assert service.update(9999, ScriptVersionUpdate(title="X")) is None


class TestScriptServiceFinalize:
    def test_finalize(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Test", script_json=SAMPLE_SCRIPT
        ))
        finalized = service.finalize(sv.id)
        assert finalized.is_finalized is True

    def test_finalize_idempotent(self, service, project_id, topic_id):
        sv = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Test", script_json=SAMPLE_SCRIPT
        ))
        service.finalize(sv.id)
        again = service.finalize(sv.id)
        assert again.is_finalized is True

    def test_finalize_nonexistent(self, service):
        assert service.finalize(9999) is None


class TestScriptServiceDiff:
    def test_diff_shows_changes(self, service, project_id, topic_id):
        sv1 = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V1", script_json={"title": "A", "scenes": []}
        ))
        sv2 = service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V2", script_json={"title": "B", "scenes": []}
        ))
        result = service.diff(sv1.id, sv2.id)
        assert result is not None
        assert result.version_a == 1
        assert result.version_b == 2
        assert len(result.changes) > 0

    def test_diff_nonexistent(self, service):
        assert service.diff(9999, 9998) is None


class TestScriptServiceList:
    def test_list_empty(self, service, project_id):
        assert service.list_for_project(project_id) == []

    def test_list_returns_versions(self, service, project_id, topic_id):
        service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V1", script_json=SAMPLE_SCRIPT
        ))
        service.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="V2", script_json=SAMPLE_SCRIPT
        ))
        versions = service.list_for_project(project_id)
        assert len(versions) == 2


# --- Router tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestScriptsRouter:
    def test_create_script(self, client, project_id, topic_id):
        resp = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "Draft", "script_json": SAMPLE_SCRIPT
        })
        assert resp.status_code == 201
        assert resp.json()["version"] == 1

    def test_list_scripts(self, client, project_id, topic_id):
        client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "V1", "script_json": SAMPLE_SCRIPT
        })
        resp = client.get(f"/api/projects/{project_id}/scripts")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_script(self, client, project_id, topic_id):
        cr = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "V1", "script_json": SAMPLE_SCRIPT
        })
        vid = cr.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/scripts/{vid}")
        assert resp.status_code == 200

    def test_update_script(self, client, project_id, topic_id):
        cr = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "Old", "script_json": SAMPLE_SCRIPT
        })
        vid = cr.json()["id"]
        resp = client.patch(f"/api/projects/{project_id}/scripts/{vid}", json={"title": "New"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    def test_update_finalized_returns_409(self, client, project_id, topic_id):
        cr = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "Test", "script_json": SAMPLE_SCRIPT
        })
        vid = cr.json()["id"]
        client.post(f"/api/projects/{project_id}/scripts/{vid}/finalize")
        resp = client.patch(f"/api/projects/{project_id}/scripts/{vid}", json={"title": "Nope"})
        assert resp.status_code == 409

    def test_finalize_script(self, client, project_id, topic_id):
        cr = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "Test", "script_json": SAMPLE_SCRIPT
        })
        vid = cr.json()["id"]
        resp = client.post(f"/api/projects/{project_id}/scripts/{vid}/finalize")
        assert resp.status_code == 200
        assert resp.json()["is_finalized"] is True

    def test_diff_scripts(self, client, project_id, topic_id):
        cr1 = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "V1", "script_json": {"title": "A", "scenes": []}
        })
        cr2 = client.post(f"/api/projects/{project_id}/scripts", json={
            "topic_id": topic_id, "title": "V2", "script_json": {"title": "B", "scenes": []}
        })
        v1 = cr1.json()["id"]
        v2 = cr2.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/scripts/diff?v1={v1}&v2={v2}")
        assert resp.status_code == 200
        assert len(resp.json()["changes"]) > 0

    def test_nonexistent_project(self, client):
        resp = client.get("/api/projects/bad-id/scripts")
        assert resp.status_code == 404
