"""Project service — CRUD and status/stage management."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from studio_api.models.project import (
    PipelineStage,
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)


class ProjectService:
    """Manages project lifecycle in SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, data: ProjectCreate) -> ProjectResponse:
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO projects (id, title, description, status, current_stage, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, data.title, data.description, ProjectStatus.DRAFT.value,
             PipelineStage.RESEARCH.value, now, now),
        )
        self._conn.commit()
        return self.get(project_id)

    def get(self, project_id: str) -> ProjectResponse | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    def list_all(self) -> list[ProjectResponse]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [self._row_to_response(r) for r in rows]

    def update(self, project_id: str, data: ProjectUpdate) -> ProjectResponse | None:
        existing = self.get(project_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        fields = []
        values = []

        if data.title is not None:
            fields.append("title = ?")
            values.append(data.title)
        if data.description is not None:
            fields.append("description = ?")
            values.append(data.description)
        if data.status is not None:
            fields.append("status = ?")
            values.append(data.status.value)
        if data.current_stage is not None:
            fields.append("current_stage = ?")
            values.append(data.current_stage.value)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        values.append(now)
        values.append(project_id)

        self._conn.execute(
            f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return self.get(project_id)

    def delete(self, project_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM projects WHERE id = ?", (project_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> ProjectResponse:
        return ProjectResponse(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=ProjectStatus(row["status"]),
            current_stage=PipelineStage(row["current_stage"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
