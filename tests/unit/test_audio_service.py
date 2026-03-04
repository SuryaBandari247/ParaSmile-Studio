"""Unit tests for AudioService and audio router."""

import json

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.audio import AudioSegmentUpdate, VoiceParams
from studio_api.models.project import ProjectCreate
from studio_api.models.script import ScriptVersionCreate
from studio_api.models.topic import TopicCreate
from studio_api.services.audio_service import (
    AudioService,
    _estimate_duration_seconds,
    _format_srt_time,
    _parse_srt_time,
)
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.script_service import ScriptService
from studio_api.services.topic_service import TopicService


SAMPLE_SCRIPT = {
    "title": "Test",
    "scenes": [
        {"scene_number": 1, "narration_text": "This is the first scene with some words to estimate duration."},
        {"scene_number": 2, "narration_text": "Second scene narration text here."},
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
def finalized_script_id(db, project_id):
    topic_id = TopicService(db).create(project_id, TopicCreate(title="AI")).id
    ss = ScriptService(db)
    sv = ss.create(project_id, ScriptVersionCreate(
        topic_id=topic_id, title="V1", script_json=SAMPLE_SCRIPT
    ))
    ss.finalize(sv.id)
    return sv.id


@pytest.fixture
def service(db):
    return AudioService(db, job_runner=JobRunner(db))


# --- SRT utility tests ---

class TestSRTUtils:
    def test_format_srt_time_zero(self):
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_format_srt_time_complex(self):
        assert _format_srt_time(3661.5) == "01:01:01,500"

    def test_parse_srt_time(self):
        assert _parse_srt_time("01:01:01,500") == pytest.approx(3661.5, abs=0.01)

    def test_roundtrip(self):
        original = 125.75
        formatted = _format_srt_time(original)
        parsed = _parse_srt_time(formatted)
        assert parsed == pytest.approx(original, abs=0.01)

    def test_estimate_duration(self):
        text = " ".join(["word"] * 150)  # 150 words = 60 seconds at 150 WPM
        assert _estimate_duration_seconds(text) == pytest.approx(60.0, abs=0.1)

    def test_estimate_duration_minimum(self):
        assert _estimate_duration_seconds("hi") >= 1.0


# --- Service tests ---

class TestAudioServiceTimeline:
    def test_generate_timeline(self, service, project_id, finalized_script_id):
        timeline = service.generate_timeline(project_id, finalized_script_id)
        assert timeline.segment_count == 2
        assert len(timeline.segments) == 2
        assert timeline.segments[0].scene_number == 1
        assert timeline.segments[1].scene_number == 2
        assert timeline.segments[0].status == "PENDING"

    def test_generate_timeline_nonexistent_script(self, service, project_id):
        with pytest.raises(ValueError, match="not found"):
            service.generate_timeline(project_id, 9999)

    def test_generate_timeline_unfinalized_script(self, db, project_id):
        topic_id = TopicService(db).create(project_id, TopicCreate(title="X")).id
        ss = ScriptService(db)
        sv = ss.create(project_id, ScriptVersionCreate(
            topic_id=topic_id, title="Draft", script_json=SAMPLE_SCRIPT
        ))
        svc = AudioService(db)
        with pytest.raises(ValueError, match="finalized"):
            svc.generate_timeline(project_id, sv.id)


class TestAudioServiceSegments:
    def test_list_segments(self, service, project_id, finalized_script_id):
        service.generate_timeline(project_id, finalized_script_id)
        segments = service.list_segments(project_id)
        assert len(segments) == 2

    def test_update_segment_text(self, service, project_id, finalized_script_id):
        timeline = service.generate_timeline(project_id, finalized_script_id)
        seg_id = timeline.segments[0].id
        updated = service.update_segment(seg_id, AudioSegmentUpdate(narration_text="New text"))
        assert updated.narration_text == "New text"

    def test_update_segment_timing(self, service, project_id, finalized_script_id):
        timeline = service.generate_timeline(project_id, finalized_script_id)
        seg_id = timeline.segments[0].id
        updated = service.update_segment(seg_id, AudioSegmentUpdate(
            start_time="00:00:01,000", end_time="00:00:05,000"
        ))
        assert updated.start_time == "00:00:01,000"
        assert updated.end_time == "00:00:05,000"

    def test_update_segment_voice_params(self, service, project_id, finalized_script_id):
        timeline = service.generate_timeline(project_id, finalized_script_id)
        seg_id = timeline.segments[0].id
        updated = service.update_segment(seg_id, AudioSegmentUpdate(
            voice_params=VoiceParams(speed=1.2, pitch=0.5, emphasis="moderate")
        ))
        assert updated.voice_params is not None
        assert updated.voice_params.speed == 1.2

    def test_update_nonexistent(self, service):
        assert service.update_segment(9999, AudioSegmentUpdate(narration_text="X")) is None


class TestAudioServicePause:
    def test_insert_pause(self, service, project_id, finalized_script_id):
        timeline = service.generate_timeline(project_id, finalized_script_id)
        seg_id = timeline.segments[0].id
        pause = service.insert_pause(project_id, seg_id, duration_ms=1000)
        assert pause.narration_text == "[pause]"
        assert pause.status == "SYNTHESIZED"

    def test_insert_pause_nonexistent(self, service, project_id):
        with pytest.raises(ValueError, match="not found"):
            service.insert_pause(project_id, 9999)


# --- Router tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestAudioRouter:
    def test_generate_timeline(self, client, project_id, finalized_script_id):
        resp = client.post(
            f"/api/projects/{project_id}/audio/timeline",
            json={"script_version_id": finalized_script_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["segment_count"] == 2

    def test_list_segments(self, client, project_id, finalized_script_id):
        client.post(
            f"/api/projects/{project_id}/audio/timeline",
            json={"script_version_id": finalized_script_id},
        )
        resp = client.get(f"/api/projects/{project_id}/audio/segments")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_segment(self, client, project_id, finalized_script_id):
        tr = client.post(
            f"/api/projects/{project_id}/audio/timeline",
            json={"script_version_id": finalized_script_id},
        )
        seg_id = tr.json()["segments"][0]["id"]
        resp = client.patch(
            f"/api/projects/{project_id}/audio/segments/{seg_id}",
            json={"narration_text": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["narration_text"] == "Updated"

    def test_insert_pause(self, client, project_id, finalized_script_id):
        tr = client.post(
            f"/api/projects/{project_id}/audio/timeline",
            json={"script_version_id": finalized_script_id},
        )
        seg_id = tr.json()["segments"][0]["id"]
        resp = client.post(
            f"/api/projects/{project_id}/audio/segments/{seg_id}/pause",
            json={"duration_ms": 750},
        )
        assert resp.status_code == 201
        assert resp.json()["narration_text"] == "[pause]"

    def test_nonexistent_project(self, client):
        resp = client.get("/api/projects/bad-id/audio/segments")
        assert resp.status_code == 404
