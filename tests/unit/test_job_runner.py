"""Unit tests for JobRunner service."""

import json
import sqlite3

import pytest

from studio_api.database import get_connection, run_migrations
from studio_api.models.job import JobStatus, JobType
from studio_api.models.project import ProjectCreate
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_id(db):
    """Create a project and return its ID."""
    svc = ProjectService(db)
    p = svc.create(ProjectCreate(title="Test Project"))
    return p.id


@pytest.fixture
def runner(db):
    return JobRunner(db)


@pytest.fixture
def broadcast_log():
    """Capture broadcast calls."""
    log = []

    def _broadcast(project_id, message):
        log.append({"project_id": project_id, "message": message})

    return log, _broadcast


class TestCreateJob:
    def test_create_returns_pending_job(self, db, runner, project_id):
        job = runner.create_job(project_id, JobType.RESEARCH_YOUTUBE.value)
        assert job.status == JobStatus.PENDING
        assert job.project_id == project_id
        assert job.job_type == "research_youtube"
        assert len(job.id) == 36

    def test_create_with_input_data(self, db, runner, project_id):
        job = runner.create_job(
            project_id, "research_reddit", input_data={"query": "python"}
        )
        assert job.input_json == {"query": "python"}

    def test_create_without_input_data(self, db, runner, project_id):
        job = runner.create_job(project_id, "render_final")
        assert job.input_json is None

    def test_create_sets_timestamps(self, db, runner, project_id):
        job = runner.create_job(project_id, "render_scene")
        assert job.created_at is not None
        assert job.updated_at is not None


class TestGetJob:
    def test_get_existing(self, db, runner, project_id):
        created = runner.create_job(project_id, "research_youtube")
        fetched = runner.get_job(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent(self, runner):
        assert runner.get_job("nonexistent") is None


class TestListJobs:
    def test_list_empty(self, runner, project_id):
        assert runner.list_jobs(project_id) == []

    def test_list_returns_project_jobs(self, db, runner, project_id):
        runner.create_job(project_id, "research_youtube")
        runner.create_job(project_id, "research_reddit")
        jobs = runner.list_jobs(project_id)
        assert len(jobs) == 2

    def test_list_filters_by_project(self, db, project_id):
        svc = ProjectService(db)
        other = svc.create(ProjectCreate(title="Other"))
        runner = JobRunner(db)
        runner.create_job(project_id, "research_youtube")
        runner.create_job(other.id, "research_reddit")
        assert len(runner.list_jobs(project_id)) == 1
        assert len(runner.list_jobs(other.id)) == 1


class TestStartJob:
    def test_start_transitions_to_running(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        started = runner.start_job(job.id)
        assert started.status == JobStatus.RUNNING

    def test_start_nonexistent_returns_none(self, runner):
        assert runner.start_job("bad-id") is None

    def test_start_already_running_returns_none(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        assert runner.start_job(job.id) is None

    def test_start_broadcasts(self, db, project_id, broadcast_log):
        log, broadcast = broadcast_log
        runner = JobRunner(db, broadcast=broadcast)
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        assert len(log) == 1
        assert log[0]["message"]["event"] == "job_started"
        assert log[0]["project_id"] == project_id


class TestCompleteJob:
    def test_complete_transitions_to_completed(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        completed = runner.complete_job(job.id, output_data={"results": [1, 2]})
        assert completed.status == JobStatus.COMPLETED
        assert completed.output_json == {"results": [1, 2]}

    def test_complete_pending_returns_none(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        assert runner.complete_job(job.id) is None

    def test_complete_broadcasts(self, db, project_id, broadcast_log):
        log, broadcast = broadcast_log
        runner = JobRunner(db, broadcast=broadcast)
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        log.clear()
        runner.complete_job(job.id, output_data={"ok": True})
        assert len(log) == 1
        assert log[0]["message"]["event"] == "job_completed"


class TestFailJob:
    def test_fail_transitions_to_failed(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        failed = runner.fail_job(job.id, "API timeout")
        assert failed.status == JobStatus.FAILED
        assert failed.error == "API timeout"

    def test_fail_pending_returns_none(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        assert runner.fail_job(job.id, "error") is None

    def test_fail_broadcasts(self, db, project_id, broadcast_log):
        log, broadcast = broadcast_log
        runner = JobRunner(db, broadcast=broadcast)
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        log.clear()
        runner.fail_job(job.id, "boom")
        assert len(log) == 1
        assert log[0]["message"]["event"] == "job_failed"
        assert log[0]["message"]["data"]["error"] == "boom"


class TestJobLifecycle:
    def test_full_success_lifecycle(self, db, runner, project_id):
        job = runner.create_job(project_id, "render_final")
        assert job.status == JobStatus.PENDING
        started = runner.start_job(job.id)
        assert started.status == JobStatus.RUNNING
        completed = runner.complete_job(job.id, {"path": "/output.mp4"})
        assert completed.status == JobStatus.COMPLETED

    def test_full_failure_lifecycle(self, db, runner, project_id):
        job = runner.create_job(project_id, "synthesize_audio")
        runner.start_job(job.id)
        failed = runner.fail_job(job.id, "Out of memory")
        assert failed.status == JobStatus.FAILED
        # Cannot complete a failed job
        assert runner.complete_job(job.id) is None

    def test_cannot_fail_completed_job(self, db, runner, project_id):
        job = runner.create_job(project_id, "research_youtube")
        runner.start_job(job.id)
        runner.complete_job(job.id)
        assert runner.fail_job(job.id, "late error") is None
