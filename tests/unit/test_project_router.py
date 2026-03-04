"""Unit tests for the projects router."""

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app


@pytest.fixture
def client():
    """TestClient with an in-memory database."""
    conn = get_connection(":memory:")
    run_migrations(conn)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: conn

    with TestClient(app) as c:
        yield c

    conn.close()


class TestCreateProject:
    def test_create_success(self, client):
        resp = client.post("/api/projects", json={"title": "My Video"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Video"
        assert data["status"] == "DRAFT"
        assert data["current_stage"] == "RESEARCH"
        assert "id" in data

    def test_create_with_description(self, client):
        resp = client.post(
            "/api/projects",
            json={"title": "Test", "description": "A video about testing"},
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "A video about testing"

    def test_create_empty_title_rejected(self, client):
        resp = client.post("/api/projects", json={"title": ""})
        assert resp.status_code == 422


class TestListProjects:
    def test_list_empty(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created(self, client):
        client.post("/api/projects", json={"title": "A"})
        client.post("/api/projects", json={"title": "B"})
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetProject:
    def test_get_existing(self, client):
        create_resp = client.post("/api/projects", json={"title": "Test"})
        pid = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test"

    def test_get_not_found(self, client):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404


class TestUpdateProject:
    def test_update_title(self, client):
        create_resp = client.post("/api/projects", json={"title": "Old"})
        pid = create_resp.json()["id"]
        resp = client.patch(f"/api/projects/{pid}", json={"title": "New"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    def test_update_status(self, client):
        create_resp = client.post("/api/projects", json={"title": "Test"})
        pid = create_resp.json()["id"]
        resp = client.patch(
            f"/api/projects/{pid}", json={"status": "IN_PROGRESS"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"

    def test_update_not_found(self, client):
        resp = client.patch("/api/projects/bad-id", json={"title": "X"})
        assert resp.status_code == 404


class TestDeleteProject:
    def test_delete_existing(self, client):
        create_resp = client.post("/api/projects", json={"title": "Test"})
        pid = create_resp.json()["id"]
        resp = client.delete(f"/api/projects/{pid}")
        assert resp.status_code == 204
        assert client.get(f"/api/projects/{pid}").status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/projects/bad-id")
        assert resp.status_code == 404


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
