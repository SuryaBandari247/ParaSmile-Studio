"""Topic service — CRUD with sequential TOPIC-NNN IDs and pitch generation."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from studio_api.models.topic import TopicCreate, TopicResponse, TopicStatus, TopicUpdate
from studio_api.services.job_runner import JobRunner

logger = logging.getLogger(__name__)


class TopicService:
    """Manages topics within a project scope."""

    def __init__(self, conn: sqlite3.Connection, job_runner: JobRunner | None = None) -> None:
        self._conn = conn
        self._job_runner = job_runner

    def create(self, project_id: str, data: TopicCreate) -> TopicResponse:
        """Create a topic with sequential TOPIC-NNN ID."""
        topic_id = self._next_id(project_id)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO topics (id, project_id, title, source, score, keywords_json, status, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (topic_id, project_id, data.title, data.source, data.score,
             json.dumps(data.keywords), TopicStatus.PENDING.value,
             json.dumps(data.metadata), now, now),
        )
        self._conn.commit()
        return self.get(topic_id)

    def get(self, topic_id: str) -> TopicResponse | None:
        row = self._conn.execute(
            "SELECT * FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    def list_for_project(self, project_id: str) -> list[TopicResponse]:
        rows = self._conn.execute(
            "SELECT * FROM topics WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        return [self._row_to_response(r) for r in rows]

    def update(self, topic_id: str, data: TopicUpdate) -> TopicResponse | None:
        existing = self.get(topic_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        fields = []
        values = []

        if data.title is not None:
            fields.append("title = ?")
            values.append(data.title)
        if data.status is not None:
            fields.append("status = ?")
            values.append(data.status.value)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        values.append(now)
        values.append(topic_id)

        self._conn.execute(
            f"UPDATE topics SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return self.get(topic_id)

    def delete(self, topic_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM topics WHERE id = ?", (topic_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def generate_pitch(self, project_id: str, topic_id: str) -> dict:
        """Generate a pitch for a topic via GPT-4o-mini."""
        if self._job_runner is None:
            raise RuntimeError("JobRunner not configured")

        topic = self.get(topic_id)
        if topic is None:
            raise ValueError(f"Topic {topic_id} not found")

        job = self._job_runner.create_job(project_id, "generate_pitch", input_data={"topic_id": topic_id})
        self._job_runner.start_job(job.id)
        try:
            from research_agent.pitch_generator import PitchGenerator
            pg = PitchGenerator()
            topic_data = [{
                "topic_name": topic.title,
                "source": topic.source,
                "trend_score": topic.score,
                "keywords": topic.keywords,
            }]
            board = pg.generate_pitches(topic_data)
            pitches = [{"title": p.title, "hook": p.hook, "context_type": p.context_type,
                        "category": p.category, "estimated_interest": p.estimated_interest}
                       for p in board.pitches]
            self._job_runner.complete_job(job.id, output_data={"pitches": pitches})
            return {"job_id": job.id, "pitches": pitches}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def _next_id(self, project_id: str) -> str:
        row = self._conn.execute(
            "SELECT id FROM topics WHERE project_id = ? AND id LIKE 'TOPIC-%' ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if row is None:
            # Check if any TOPIC-NNN exists globally to avoid PK collision
            global_row = self._conn.execute(
                "SELECT id FROM topics WHERE id LIKE 'TOPIC-%' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if global_row is None:
                return "TOPIC-001"
            num = int(global_row["id"].split("-")[1])
            return f"TOPIC-{num + 1:03d}"
        current = row["id"]  # e.g. "TOPIC-003"
        num = int(current.split("-")[1])
        return f"TOPIC-{num + 1:03d}"

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> TopicResponse:
        keywords = row["keywords_json"]
        if keywords and isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except json.JSONDecodeError:
                keywords = []
        metadata = row["metadata_json"]
        if metadata and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        return TopicResponse(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            source=row["source"],
            score=row["score"],
            keywords=keywords or [],
            status=TopicStatus(row["status"]),
            metadata=metadata or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
