"""Unit tests for the effects API router."""

import pytest
from fastapi.testclient import TestClient

from studio_api.routers.effects import router

from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestListEffects:
    def test_list_all(self):
        resp = client.get("/api/effects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 17
        ids = {e["identifier"] for e in data}
        assert "timeseries" in ids
        assert "text_overlay" in ids

    def test_filter_by_category(self):
        resp = client.get("/api/effects?category=data")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["category"] == "data" for e in data)

    def test_invalid_category(self):
        resp = client.get("/api/effects?category=bogus")
        assert resp.status_code == 400


class TestGetEffect:
    def test_found(self):
        resp = client.get("/api/effects/timeseries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["identifier"] == "timeseries"
        assert "parameter_schema" in data
        assert "sync_points" in data
        assert "quality_profiles" in data

    def test_not_found(self):
        resp = client.get("/api/effects/nonexistent")
        assert resp.status_code == 404


class TestListAliases:
    def test_returns_aliases(self):
        resp = client.get("/api/effects/aliases")
        assert resp.status_code == 200
        data = resp.json()
        assert "aliases" in data
        assert "line_chart" in data["aliases"]
