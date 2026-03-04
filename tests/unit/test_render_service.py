"""Unit tests for RenderService and render/music routers."""

import json
import tempfile

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.project import ProjectCreate
from studio_api.models.scene import MusicSettings
from studio_api.models.script import ScriptVersionCreate
from studio_api.models.topic import TopicCreate
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.render_service import RenderService
from studio_api.services.script_service import ScriptService
from studio_api.services.topic_service import TopicService
from studio_api.services.visual_service import VisualService


SAMPLE_SCRIPT = {
    "title": "Test",
    "scenes": [
        {"scene_number": 1, "narration_text": "Hello",
         "visual_instruction": {"type": "text_overlay", "data": {"text": "Hi"}}},
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
def scenes_created(db, project_id):
    """Create a project with scenes from a finalized script."""
    topic_id = TopicService(db).create(project_id, TopicCreate(title="AI")).id
    ss = ScriptService(db)
    sv = ss.create(project_id, ScriptVersionCreate(
        topic_id=topic_id, title="V1", script_json=SAMPLE_SCRIPT
    ))
    ss.finalize(sv.id)
    vs = VisualService(db)
    return vs.create_scenes_from_script(project_id, sv.id)


@pytest.fixture
def service(db):
    return RenderService(db, job_runner=JobRunner(db))


class TestGetSceneOrder:
    def test_empty(self, service, project_id):
        assert service.get_scene_order(project_id) == []

    def test_returns_scenes(self, service, project_id, scenes_created):
        order = service.get_scene_order(project_id)
        assert len(order) == 1
        assert order[0]["scene_number"] == 1


class TestReorderScenes:
    def test_reorder(self, db, project_id):
        # Create 2 scenes manually
        topic_id = TopicService(db).create(project_id, TopicCreate(title="X")).id
        ss = ScriptService(db)
        script = {"title": "T", "scenes": [
            {"scene_number": 1, "narration_text": "A", "visual_instruction": {"type": "text_overlay", "data": {"text": "1"}}},
            {"scene_number": 2, "narration_text": "B", "visual_instruction": {"type": "text_overlay", "data": {"text": "2"}}},
        ]}
        sv = ss.create(project_id, ScriptVersionCreate(topic_id=topic_id, title="V1", script_json=script))
        ss.finalize(sv.id)
        vs = VisualService(db)
        scenes = vs.create_scenes_from_script(project_id, sv.id)

        svc = RenderService(db)
        # Reverse order
        reordered = svc.reorder_scenes(project_id, [scenes[1].id, scenes[0].id])
        assert reordered[0]["scene_number"] == 1
        assert reordered[0]["id"] == scenes[1].id


class TestStartRender:
    def test_render_no_scenes_fails(self, service, project_id):
        with pytest.raises(ValueError, match="No rendered scenes"):
            service.start_render(project_id)

    def test_render_with_rendered_scene(self, db, project_id, scenes_created):
        # Mark scene as rendered
        db.execute(
            "UPDATE scenes SET rendered_path = '/output/scene.mp4', status = 'RENDERED' WHERE id = ?",
            (scenes_created[0].id,),
        )
        db.commit()

        svc = RenderService(db, job_runner=JobRunner(db))
        result = svc.start_render(project_id)
        assert result["status"] == "COMPLETED"
        assert result["output"]["scene_count"] == 1


class TestGetRenderStatus:
    def test_no_render_job(self, service, project_id):
        assert service.get_render_status(project_id) is None

    def test_returns_latest_render(self, db, project_id, scenes_created):
        db.execute(
            "UPDATE scenes SET rendered_path = '/out.mp4', status = 'RENDERED' WHERE id = ?",
            (scenes_created[0].id,),
        )
        db.commit()
        svc = RenderService(db, job_runner=JobRunner(db))
        svc.start_render(project_id)
        status = svc.get_render_status(project_id)
        assert status is not None
        assert status["status"] == "COMPLETED"


class TestMusicSettings:
    def test_update_settings(self, db, project_id):
        with tempfile.TemporaryDirectory() as tmp:
            from studio_api.services.artifact_store import ArtifactStore
            # Patch the artifact store base dir
            svc = RenderService(db)
            store = ArtifactStore(db, base_dir=tmp)
            result = store.store(
                project_id, "music_settings", "settings.json",
                json.dumps({"volume": 50, "fade_in_ms": 1000, "fade_out_ms": 2000}).encode(),
                metadata={"volume": 50, "fade_in_ms": 1000, "fade_out_ms": 2000},
            )
            assert result["metadata"]["volume"] == 50


# --- Router tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestRenderRouter:
    def test_render_status_no_job(self, client, project_id):
        resp = client.get(f"/api/projects/{project_id}/render/status")
        assert resp.status_code == 404

    def test_reorder_scenes(self, client, db, project_id):
        topic_id = TopicService(db).create(project_id, TopicCreate(title="X")).id
        ss = ScriptService(db)
        script = {"title": "T", "scenes": [
            {"scene_number": 1, "narration_text": "A", "visual_instruction": {"type": "text_overlay", "data": {"text": "1"}}},
            {"scene_number": 2, "narration_text": "B", "visual_instruction": {"type": "text_overlay", "data": {"text": "2"}}},
        ]}
        sv = ss.create(project_id, ScriptVersionCreate(topic_id=topic_id, title="V1", script_json=script))
        ss.finalize(sv.id)
        vs = VisualService(db)
        scenes = vs.create_scenes_from_script(project_id, sv.id)

        resp = client.post(
            f"/api/projects/{project_id}/render/reorder",
            json={"scene_ids": [scenes[1].id, scenes[0].id]},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["id"] == scenes[1].id

    def test_nonexistent_project(self, client):
        resp = client.get("/api/projects/bad-id/render/status")
        assert resp.status_code == 404


class TestMusicRouter:
    def test_upload_invalid_format(self, client, project_id):
        resp = client.post(
            f"/api/projects/{project_id}/music/upload",
            files={"file": ("track.txt", b"not audio", "text/plain")},
        )
        assert resp.status_code == 422

    def test_nonexistent_project(self, client):
        resp = client.patch(
            "/api/projects/bad-id/music/settings",
            json={"volume": 50},
        )
        assert resp.status_code == 404
