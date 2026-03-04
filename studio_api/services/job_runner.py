"""Job runner service — create, update, and manage background jobs."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from studio_api.models.job import JobResponse, JobStatus, JobType

logger = logging.getLogger(__name__)


class JobRunner:
    """Manages job lifecycle in SQLite and broadcasts status via callback."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        broadcast: Callable[[str, dict], None] | None = None,
    ) -> None:
        self._conn = conn
        self._broadcast = broadcast  # (project_id, message_dict) -> None

    def create_job(
        self,
        project_id: str,
        job_type: str,
        input_data: dict | None = None,
    ) -> JobResponse:
        """Insert a new PENDING job and return it."""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO jobs (id, project_id, job_type, status, input_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, project_id, job_type, JobStatus.PENDING.value,
             json.dumps(input_data) if input_data else None, now, now),
        )
        self._conn.commit()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobResponse | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    def list_jobs(self, project_id: str) -> list[JobResponse]:
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [self._row_to_response(r) for r in rows]

    def start_job(self, job_id: str) -> JobResponse | None:
        """Transition job from PENDING to RUNNING and broadcast."""
        job = self.get_job(job_id)
        if job is None or job.status != JobStatus.PENDING:
            return None
        return self._update_status(job_id, JobStatus.RUNNING, broadcast_event="job_started")

    def complete_job(
        self, job_id: str, output_data: dict | None = None
    ) -> JobResponse | None:
        """Transition job from RUNNING to COMPLETED and broadcast."""
        job = self.get_job(job_id)
        if job is None or job.status != JobStatus.RUNNING:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE jobs SET status = ?, output_json = ?, updated_at = ? WHERE id = ?",
            (JobStatus.COMPLETED.value, json.dumps(output_data) if output_data else None, now, job_id),
        )
        self._conn.commit()
        updated = self.get_job(job_id)
        self._emit(updated, "job_completed")
        return updated

    def fail_job(self, job_id: str, error: str) -> JobResponse | None:
        """Transition job from RUNNING to FAILED and broadcast."""
        job = self.get_job(job_id)
        if job is None or job.status != JobStatus.RUNNING:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (JobStatus.FAILED.value, error, now, job_id),
        )
        self._conn.commit()
        updated = self.get_job(job_id)
        self._emit(updated, "job_failed")
        return updated

    def _update_status(
        self, job_id: str, status: JobStatus, broadcast_event: str | None = None
    ) -> JobResponse:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, job_id),
        )
        self._conn.commit()
        updated = self.get_job(job_id)
        if broadcast_event:
            self._emit(updated, broadcast_event)
        return updated

    def _emit(self, job: JobResponse, event: str) -> None:
        if self._broadcast is None or job is None:
            return
        message = {
            "event": event,
            "job_id": job.id,
            "job_type": job.job_type,
            "data": {},
        }
        if event == "job_completed" and job.output_json:
            message["data"]["output"] = job.output_json
        if event == "job_failed" and job.error:
            message["data"]["error"] = job.error
        try:
            self._broadcast(job.project_id, message)
        except Exception:
            logger.exception("Failed to broadcast %s for job %s", event, job.id)

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> JobResponse:
        output = row["output_json"]
        if output and isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                pass
        input_data = row["input_json"]
        if input_data and isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                pass
        return JobResponse(
            id=row["id"],
            project_id=row["project_id"],
            job_type=row["job_type"],
            status=JobStatus(row["status"]),
            input_json=input_data,
            output_json=output,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
