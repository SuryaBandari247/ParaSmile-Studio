"""Unit tests for ProjectService."""

import sqlite3

import pytest

from studio_api.database import get_connection, run_migrations
from studio_api.models.project import (
    PipelineStage,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
)
from studio_api.services.project_service import ProjectService


@pytest.fixture
def db():
    """In-memory SQLite database with migrations applied."""
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def service(db):
    return ProjectService(db)


class TestProjectServiceCreate:
    def test_create_returns_project(self, service):
        project = service.create(ProjectCreate(title="Test Video"))
        assert project.title == "Test Video"
        assert project.description == ""
        assert project.status == ProjectStatus.DRAFT
        assert project.current_stage == PipelineStage.RESEARCH

    def test_create_assigns_uuid(self, service):
        p1 = service.create(ProjectCreate(title="A"))
        p2 = service.create(ProjectCreate(title="B"))
        assert p1.id != p2.id
        assert len(p1.id) == 36  # UUID format

    def test_create_with_description(self, service):
        project = service.create(
            ProjectCreate(title="Test", description="A description")
        )
        assert project.description == "A description"

    def test_create_sets_timestamps(self, service):
        project = service.create(ProjectCreate(title="Test"))
        assert project.created_at is not None
        assert project.updated_at is not None


class TestProjectServiceGet:
    def test_get_existing(self, service):
        created = service.create(ProjectCreate(title="Test"))
        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test"

    def test_get_nonexistent(self, service):
        result = service.get("nonexistent-id")
        assert result is None


class TestProjectServiceList:
    def test_list_empty(self, service):
        assert service.list_all() == []

    def test_list_multiple(self, service):
        service.create(ProjectCreate(title="A"))
        service.create(ProjectCreate(title="B"))
        projects = service.list_all()
        assert len(projects) == 2


class TestProjectServiceUpdate:
    def test_update_title(self, service):
        created = service.create(ProjectCreate(title="Old"))
        updated = service.update(created.id, ProjectUpdate(title="New"))
        assert updated.title == "New"

    def test_update_status(self, service):
        created = service.create(ProjectCreate(title="Test"))
        updated = service.update(
            created.id, ProjectUpdate(status=ProjectStatus.IN_PROGRESS)
        )
        assert updated.status == ProjectStatus.IN_PROGRESS

    def test_update_stage(self, service):
        created = service.create(ProjectCreate(title="Test"))
        updated = service.update(
            created.id, ProjectUpdate(current_stage=PipelineStage.SCRIPT)
        )
        assert updated.current_stage == PipelineStage.SCRIPT

    def test_update_nonexistent(self, service):
        result = service.update("bad-id", ProjectUpdate(title="X"))
        assert result is None

    def test_update_no_fields(self, service):
        created = service.create(ProjectCreate(title="Test"))
        updated = service.update(created.id, ProjectUpdate())
        assert updated.title == "Test"


class TestProjectServiceDelete:
    def test_delete_existing(self, service):
        created = service.create(ProjectCreate(title="Test"))
        assert service.delete(created.id) is True
        assert service.get(created.id) is None

    def test_delete_nonexistent(self, service):
        assert service.delete("bad-id") is False
