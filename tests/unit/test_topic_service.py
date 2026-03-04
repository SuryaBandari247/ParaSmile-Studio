"""Unit tests for TopicService and topics router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.project import ProjectCreate
from studio_api.models.topic import TopicCreate, TopicStatus, TopicUpdate
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.topic_service import TopicService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_id(db):
    svc = ProjectService(db)
    return svc.create(ProjectCreate(title="Test")).id


@pytest.fixture
def service(db):
    return TopicService(db, job_runner=JobRunner(db))


# --- Service-level tests ---

class TestTopicServiceCreate:
    def test_create_first_topic(self, service, project_id):
        topic = service.create(project_id, TopicCreate(title="AI Trends"))
        assert topic.id == "TOPIC-001"
        assert topic.title == "AI Trends"
        assert topic.source == "manual"
        assert topic.status == TopicStatus.PENDING

    def test_create_sequential_ids(self, service, project_id):
        t1 = service.create(project_id, TopicCreate(title="A"))
        t2 = service.create(project_id, TopicCreate(title="B"))
        t3 = service.create(project_id, TopicCreate(title="C"))
        assert t1.id == "TOPIC-001"
        assert t2.id == "TOPIC-002"
        assert t3.id == "TOPIC-003"

    def test_create_with_metadata(self, service, project_id):
        topic = service.create(project_id, TopicCreate(
            title="Rust", source="reddit", score=8.5,
            keywords=["rust", "programming"],
            metadata={"rpm_estimate": 1200},
        ))
        assert topic.source == "reddit"
        assert topic.score == 8.5
        assert topic.keywords == ["rust", "programming"]
        assert topic.metadata == {"rpm_estimate": 1200}

    def test_ids_globally_unique(self, db):
        svc = ProjectService(db)
        p1 = svc.create(ProjectCreate(title="P1")).id
        p2 = svc.create(ProjectCreate(title="P2")).id
        ts = TopicService(db)
        t1 = ts.create(p1, TopicCreate(title="A"))
        t2 = ts.create(p2, TopicCreate(title="B"))
        assert t1.id == "TOPIC-001"
        assert t2.id == "TOPIC-002"


class TestTopicServiceGet:
    def test_get_existing(self, service, project_id):
        created = service.create(project_id, TopicCreate(title="Test"))
        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent(self, service):
        assert service.get("TOPIC-999") is None


class TestTopicServiceList:
    def test_list_empty(self, service, project_id):
        assert service.list_for_project(project_id) == []

    def test_list_returns_project_topics(self, service, project_id):
        service.create(project_id, TopicCreate(title="A"))
        service.create(project_id, TopicCreate(title="B"))
        topics = service.list_for_project(project_id)
        assert len(topics) == 2
        assert topics[0].id == "TOPIC-001"
        assert topics[1].id == "TOPIC-002"


class TestTopicServiceUpdate:
    def test_update_title(self, service, project_id):
        topic = service.create(project_id, TopicCreate(title="Old"))
        updated = service.update(topic.id, TopicUpdate(title="New"))
        assert updated.title == "New"

    def test_update_status(self, service, project_id):
        topic = service.create(project_id, TopicCreate(title="Test"))
        updated = service.update(topic.id, TopicUpdate(status=TopicStatus.SELECTED))
        assert updated.status == TopicStatus.SELECTED

    def test_update_nonexistent(self, service):
        assert service.update("TOPIC-999", TopicUpdate(title="X")) is None

    def test_update_no_fields(self, service, project_id):
        topic = service.create(project_id, TopicCreate(title="Test"))
        updated = service.update(topic.id, TopicUpdate())
        assert updated.title == "Test"


class TestTopicServiceDelete:
    def test_delete_existing(self, service, project_id):
        topic = service.create(project_id, TopicCreate(title="Test"))
        assert service.delete(topic.id) is True
        assert service.get(topic.id) is None

    def test_delete_nonexistent(self, service):
        assert service.delete("TOPIC-999") is False


# --- Router-level tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestTopicsRouter:
    def test_create_topic(self, client, project_id):
        resp = client.post(
            f"/api/projects/{project_id}/topics",
            json={"title": "AI Trends"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "TOPIC-001"
        assert data["title"] == "AI Trends"

    def test_list_topics(self, client, project_id):
        client.post(f"/api/projects/{project_id}/topics", json={"title": "A"})
        client.post(f"/api/projects/{project_id}/topics", json={"title": "B"})
        resp = client.get(f"/api/projects/{project_id}/topics")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_topic(self, client, project_id):
        create_resp = client.post(
            f"/api/projects/{project_id}/topics", json={"title": "Test"}
        )
        tid = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/topics/{tid}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test"

    def test_get_topic_not_found(self, client, project_id):
        resp = client.get(f"/api/projects/{project_id}/topics/TOPIC-999")
        assert resp.status_code == 404

    def test_update_topic(self, client, project_id):
        create_resp = client.post(
            f"/api/projects/{project_id}/topics", json={"title": "Old"}
        )
        tid = create_resp.json()["id"]
        resp = client.patch(
            f"/api/projects/{project_id}/topics/{tid}",
            json={"title": "New"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    def test_update_topic_status(self, client, project_id):
        create_resp = client.post(
            f"/api/projects/{project_id}/topics", json={"title": "Test"}
        )
        tid = create_resp.json()["id"]
        resp = client.patch(
            f"/api/projects/{project_id}/topics/{tid}",
            json={"status": "SELECTED"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "SELECTED"

    def test_delete_topic(self, client, project_id):
        create_resp = client.post(
            f"/api/projects/{project_id}/topics", json={"title": "Test"}
        )
        tid = create_resp.json()["id"]
        resp = client.delete(f"/api/projects/{project_id}/topics/{tid}")
        assert resp.status_code == 204
        assert client.get(f"/api/projects/{project_id}/topics/{tid}").status_code == 404

    def test_nonexistent_project(self, client):
        resp = client.get("/api/projects/bad-id/topics")
        assert resp.status_code == 404
