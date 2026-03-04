"""Artifact store service — versioned file storage."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from studio_api.config import StudioConfig

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Manages versioned artifact storage on disk and metadata in SQLite."""

    def __init__(self, conn: sqlite3.Connection, base_dir: str | None = None) -> None:
        self._conn = conn
        self._base_dir = base_dir or StudioConfig.ARTIFACTS_DIR

    def store(
        self,
        project_id: str,
        artifact_type: str,
        filename: str,
        data: bytes,
        job_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Store a new artifact version. Returns artifact record dict."""
        version = self._next_version(project_id, artifact_type)
        rel_path = os.path.join(
            project_id, artifact_type, f"v{version}", filename
        )
        abs_path = os.path.join(self._base_dir, rel_path)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)

        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "INSERT INTO artifacts (project_id, job_id, artifact_type, version, file_path, metadata_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, job_id, artifact_type, version, rel_path,
             json.dumps(metadata) if metadata else None, now),
        )
        self._conn.commit()

        return {
            "id": cursor.lastrowid,
            "project_id": project_id,
            "job_id": job_id,
            "artifact_type": artifact_type,
            "version": version,
            "file_path": rel_path,
            "metadata": metadata,
            "created_at": now,
        }

    def get(self, artifact_id: int) -> dict | None:
        """Get artifact record by ID."""
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_artifacts(
        self, project_id: str, artifact_type: str | None = None
    ) -> list[dict]:
        """List artifacts for a project, optionally filtered by type."""
        if artifact_type:
            rows = self._conn.execute(
                "SELECT * FROM artifacts WHERE project_id = ? AND artifact_type = ? ORDER BY version DESC",
                (project_id, artifact_type),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_latest(self, project_id: str, artifact_type: str) -> dict | None:
        """Get the latest version of an artifact type for a project."""
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE project_id = ? AND artifact_type = ? ORDER BY version DESC LIMIT 1",
            (project_id, artifact_type),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_absolute_path(self, rel_path: str) -> str:
        """Resolve a relative artifact path to an absolute path."""
        return os.path.join(self._base_dir, rel_path)

    def read(self, rel_path: str) -> bytes | None:
        """Read artifact file contents."""
        abs_path = self.get_absolute_path(rel_path)
        if not os.path.exists(abs_path):
            return None
        with open(abs_path, "rb") as f:
            return f.read()

    def _next_version(self, project_id: str, artifact_type: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version) as max_v FROM artifacts WHERE project_id = ? AND artifact_type = ?",
            (project_id, artifact_type),
        ).fetchone()
        current = row["max_v"] if row and row["max_v"] is not None else 0
        return current + 1

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        meta = row["metadata_json"]
        if meta and isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                pass
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "job_id": row["job_id"],
            "artifact_type": row["artifact_type"],
            "version": row["version"],
            "file_path": row["file_path"],
            "metadata": meta,
            "created_at": row["created_at"],
        }
