"""Unit tests for WebSocket connection manager and endpoint."""

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.routers.websocket import ConnectionManager, manager


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestConnectionManager:
    def test_initial_state(self):
        mgr = ConnectionManager()
        assert mgr.get_connection_count("proj-1") == 0
        assert mgr.get_all_project_ids() == []

    def test_broadcast_sync_no_loop(self):
        """broadcast_sync should not raise when no event loop is running."""
        mgr = ConnectionManager()
        mgr.broadcast_sync("proj-1", {"event": "test"})  # should be a no-op


class TestWebSocketEndpoint:
    def test_connect_and_ping(self, client):
        with client.websocket_connect("/ws/projects/test-project") as ws:
            ws.send_text("ping")
            resp = ws.receive_text()
            assert resp == "pong"

    def test_multiple_connections(self, client):
        with client.websocket_connect("/ws/projects/proj-1") as ws1:
            with client.websocket_connect("/ws/projects/proj-1") as ws2:
                ws1.send_text("ping")
                assert ws1.receive_text() == "pong"
                ws2.send_text("ping")
                assert ws2.receive_text() == "pong"

    def test_different_projects(self, client):
        with client.websocket_connect("/ws/projects/proj-1") as ws1:
            with client.websocket_connect("/ws/projects/proj-2") as ws2:
                ws1.send_text("ping")
                assert ws1.receive_text() == "pong"
                ws2.send_text("ping")
                assert ws2.receive_text() == "pong"

    def test_disconnect_cleanup(self, client):
        with client.websocket_connect("/ws/projects/proj-1"):
            assert manager.get_connection_count("proj-1") >= 1
        # After disconnect, count should be 0
        assert manager.get_connection_count("proj-1") == 0
