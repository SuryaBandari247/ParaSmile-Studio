"""Unit tests for VisualService and visuals router."""

import json

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.project import ProjectCreate
from studio_api.models.scene import SceneUpdate
from studio_api.models.script import ScriptVersionCreate
from studio_api.models.topic import TopicCreate
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.script_service import ScriptService
from studio_api.services.topic_service import TopicService
from studio_api.services.visual_service import VisualService


SAMPLE_SCRIPT = {
    "title": "Test",
    "scenes": [
        {
            "scene_number": 1,
            "narration_text": "Hello",
            "visual_instruction": {"type": "text_overlay", "title": "Intro", "data": {"text": "Welcome"}},
        },
        {
            "scene_number": 2,
            "narration_text": "Charts",
            "visual_instruction": {"type": "bar_chart", "title": "Stats", "data": {"labels": ["A"], "values": [10]}},
        },
    ],
}


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
def script_version_id(db, project_id):
    topic_id = TopicService(db).create(project_id, TopicCreate(title="AI")).id
    ss = ScriptService(db)
    sv = ss.create(project_id, ScriptVersionCreate(
        topic_id=topic_id, title="V1", script_json=SAMPLE_SCRIPT
    ))
    ss.finalize(sv.id)
    return sv.id


@pytest.fixture
def service(db):
    return VisualService(db, job_runner=JobRunner(db))


class TestCreateScenesFromScript:
    def test_creates_scenes(self, service, project_id, script_version_id):
        scenes = service.create_scenes_from_script(project_id, script_version_id)
        assert len(scenes) == 2
        assert scenes[0].scene_number == 1
        assert scenes[0].visual_type == "text_overlay"
        assert scenes[0].visual_data["text"] == "Welcome"
        assert scenes[1].visual_type == "bar_chart"

    def test_nonexistent_script(self, service, project_id):
        with pytest.raises(ValueError, match="not found"):
            service.create_scenes_from_script(project_id, 9999)


class TestListScenes:
    def test_list_empty(self, service, project_id):
        assert service.list_scenes(project_id) == []

    def test_list_after_create(self, service, project_id, script_version_id):
        service.create_scenes_from_script(project_id, script_version_id)
        scenes = service.list_scenes(project_id)
        assert len(scenes) == 2


class TestUpdateScene:
    def test_update_visual_type(self, service, project_id, script_version_id):
        scenes = service.create_scenes_from_script(project_id, script_version_id)
        updated = service.update_scene(scenes[0].id, SceneUpdate(visual_type="code_snippet"))
        assert updated.visual_type == "code_snippet"

    def test_update_visual_data(self, service, project_id, script_version_id):
        scenes = service.create_scenes_from_script(project_id, script_version_id)
        updated = service.update_scene(scenes[0].id, SceneUpdate(visual_data={"text": "New"}))
        assert updated.visual_data == {"text": "New"}

    def test_update_stock_video_path(self, service, project_id, script_version_id):
        scenes = service.create_scenes_from_script(project_id, script_version_id)
        updated = service.update_scene(scenes[0].id, SceneUpdate(stock_video_path="/path/to/video.mp4"))
        assert updated.stock_video_path == "/path/to/video.mp4"

    def test_update_nonexistent(self, service):
        assert service.update_scene(9999, SceneUpdate(visual_type="x")) is None


class TestGetScene:
    def test_get_existing(self, service, project_id, script_version_id):
        scenes = service.create_scenes_from_script(project_id, script_version_id)
        fetched = service.get_scene(scenes[0].id)
        assert fetched is not None
        assert fetched.id == scenes[0].id

    def test_get_nonexistent(self, service):
        assert service.get_scene(9999) is None


# --- Router tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestVisualsRouter:
    def test_create_scenes(self, client, project_id, script_version_id):
        resp = client.post(
            f"/api/projects/{project_id}/scenes",
            json={"script_version_id": script_version_id},
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 2

    def test_list_scenes(self, client, project_id, script_version_id):
        client.post(f"/api/projects/{project_id}/scenes", json={"script_version_id": script_version_id})
        resp = client.get(f"/api/projects/{project_id}/scenes")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_scene(self, client, project_id, script_version_id):
        cr = client.post(f"/api/projects/{project_id}/scenes", json={"script_version_id": script_version_id})
        sid = cr.json()[0]["id"]
        resp = client.patch(f"/api/projects/{project_id}/scenes/{sid}", json={"visual_type": "code_snippet"})
        assert resp.status_code == 200
        assert resp.json()["visual_type"] == "code_snippet"

    def test_select_footage(self, client, project_id, script_version_id):
        cr = client.post(f"/api/projects/{project_id}/scenes", json={"script_version_id": script_version_id})
        sid = cr.json()[0]["id"]
        resp = client.post(
            f"/api/projects/{project_id}/scenes/{sid}/select-footage",
            json={"stock_video_path": "/path/clip.mp4"},
        )
        assert resp.status_code == 200
        assert resp.json()["stock_video_path"] == "/path/clip.mp4"

    def test_nonexistent_project(self, client):
        resp = client.get("/api/projects/bad-id/scenes")
        assert resp.status_code == 404
