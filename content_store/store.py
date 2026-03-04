"""SQLite-backed persistence for pipeline artifacts."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from content_store.exceptions import ContentStoreError

if TYPE_CHECKING:
    from script_generator.models import VideoScript

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS scripts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    raw_script      TEXT    NOT NULL,
    video_script_json TEXT  NOT NULL,
    selected_topic_json TEXT,
    documents_used  INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL,
    word_count      INTEGER NOT NULL,
    scene_count     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS search_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    search_results_json TEXT    NOT NULL,
    query_date          TEXT    NOT NULL,
    topics_found        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS script_links (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_script_id  INTEGER NOT NULL REFERENCES scripts(id),
    target_script_id  INTEGER NOT NULL REFERENCES scripts(id),
    link_type         TEXT    NOT NULL,
    note              TEXT,
    created_at        TEXT    NOT NULL,
    UNIQUE(source_script_id, target_script_id, link_type)
);
"""


class ContentStore:
    """SQLite-backed persistence for pipeline artifacts.

    Uses WAL journal mode and enforces foreign keys.
    All public query methods return plain dicts.
    """

    def __init__(self, db_path: str = ".data/content_store.db") -> None:
        """Open (or create) the database at *db_path*.

        Creates parent directories if missing.
        Enables WAL mode and foreign keys.
        Creates tables if they do not exist.
        """
        try:
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA foreign_keys=ON;")
            self.conn.executescript(_SCHEMA_SQL)
        except Exception as exc:
            raise ContentStoreError(f"Failed to initialise database at {db_path}: {exc}") from exc

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self) -> ContentStore:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit — calls close()."""
        self.close()

    # ------------------------------------------------------------------
    # Script CRUD
    # ------------------------------------------------------------------

    def save_script(
        self,
        video_script: VideoScript,
        raw_script: str,
        selected_topic: dict | None,
        documents_used: int,
    ) -> int:
        """Insert a script record. Returns the new row id.

        Serializes video_script via ScriptSerializer.
        Computes scene_count from len(video_script.scenes).
        Sets created_at to current UTC time.
        Raises ContentStoreError on failure.
        """
        try:
            from script_generator.serializer import ScriptSerializer

            serializer = ScriptSerializer()
            video_script_json = serializer.serialize(video_script)
            selected_topic_json = json.dumps(selected_topic) if selected_topic is not None else None
            scene_count = len(video_script.scenes)
            word_count = video_script.total_word_count
            created_at = datetime.now(timezone.utc).isoformat()

            cursor = self.conn.execute(
                "INSERT INTO scripts "
                "(title, raw_script, video_script_json, selected_topic_json, "
                "documents_used, created_at, word_count, scene_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    video_script.title,
                    raw_script,
                    video_script_json,
                    selected_topic_json,
                    documents_used,
                    created_at,
                    word_count,
                    scene_count,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid
        except ContentStoreError:
            raise
        except Exception as exc:
            raise ContentStoreError(f"Failed to save script: {exc}") from exc

    def get_script(self, script_id: int) -> dict | None:
        """Return a single script record as a dict, or None if not found."""
        row = self.conn.execute(
            "SELECT * FROM scripts WHERE id = ?", (script_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_scripts(
        self,
        *,
        category: str | None = None,
        keyword: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Return script records matching filters, ordered by created_at DESC.

        category: match against selected_topic_json -> category field.
        keyword: case-insensitive LIKE match on title or raw_script.
        start_date / end_date: inclusive ISO 8601 date range on created_at.
        """
        clauses: list[str] = []
        params: list[object] = []

        if category is not None:
            clauses.append(
                "json_extract(selected_topic_json, '$.category') = ?"
            )
            params.append(category)

        if keyword is not None:
            clauses.append(
                "(title LIKE ? COLLATE NOCASE OR raw_script LIKE ? COLLATE NOCASE)"
            )
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern])

        if start_date is not None:
            clauses.append("created_at >= ?")
            params.append(start_date)

        if end_date is not None:
            clauses.append("created_at <= ?")
            params.append(end_date)

        sql = "SELECT * FROM scripts"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Search Session CRUD
    # ------------------------------------------------------------------

    def save_search_session(self, search_results: dict) -> int:
        """Insert a search session record. Returns the new row id.

        Computes topics_found from len(search_results.get("topics", [])).
        Sets query_date to current UTC time.
        Raises ContentStoreError on failure.
        """
        try:
            search_results_json = json.dumps(search_results)
            topics_found = len(search_results.get("topics", []))
            query_date = datetime.now(timezone.utc).isoformat()

            cursor = self.conn.execute(
                "INSERT INTO search_sessions "
                "(search_results_json, query_date, topics_found) "
                "VALUES (?, ?, ?)",
                (search_results_json, query_date, topics_found),
            )
            self.conn.commit()
            return cursor.lastrowid
        except ContentStoreError:
            raise
        except Exception as exc:
            raise ContentStoreError(f"Failed to save search session: {exc}") from exc

    def get_search_session(self, session_id: int) -> dict | None:
        """Return a single search session record as a dict, or None."""
        row = self.conn.execute(
            "SELECT * FROM search_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_search_sessions(self) -> list[dict]:
        """Return all search session records ordered by query_date DESC."""
        rows = self.conn.execute(
            "SELECT * FROM search_sessions ORDER BY query_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Script Links
    # ------------------------------------------------------------------

    def link_scripts(
        self,
        source_id: int,
        target_id: int,
        link_type: str,
        note: str | None = None,
    ) -> int:
        """Create a directional link between two scripts. Returns the link row id.

        Validates both script ids exist.
        Raises ContentStoreError if either id is missing or link is duplicate.
        Sets created_at to current UTC time.
        """
        try:
            # Validate source exists
            row = self.conn.execute(
                "SELECT id FROM scripts WHERE id = ?", (source_id,)
            ).fetchone()
            if row is None:
                raise ContentStoreError(
                    f"Source script with id {source_id} does not exist"
                )

            # Validate target exists
            row = self.conn.execute(
                "SELECT id FROM scripts WHERE id = ?", (target_id,)
            ).fetchone()
            if row is None:
                raise ContentStoreError(
                    f"Target script with id {target_id} does not exist"
                )

            created_at = datetime.now(timezone.utc).isoformat()
            cursor = self.conn.execute(
                "INSERT INTO script_links "
                "(source_script_id, target_script_id, link_type, note, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, link_type, note, created_at),
            )
            self.conn.commit()
            return cursor.lastrowid
        except ContentStoreError:
            raise
        except sqlite3.IntegrityError as exc:
            raise ContentStoreError(
                f"Duplicate link: ({source_id}, {target_id}, {link_type!r})"
            ) from exc
        except Exception as exc:
            raise ContentStoreError(f"Failed to link scripts: {exc}") from exc

    def get_script_links(self, script_id: int) -> list[dict]:
        """Return explicit link records for a script (both directions).

        Returns empty list if script_id does not exist.
        """
        rows = self.conn.execute(
            "SELECT * FROM script_links "
            "WHERE source_script_id = ? OR target_script_id = ?",
            (script_id, script_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def find_related_scripts(self, script_id: int) -> list[dict]:
        """Find scripts related to the given script through:
        1. Explicit links (both directions) — relationship_type="linked"
        2. Same category in selected_topic_json — relationship_type="same_category"
        3. Overlapping title keywords — relationship_type="keyword_overlap"

        Returns empty list if script_id does not exist.
        """
        # Check script exists and get its data
        script = self.get_script(script_id)
        if script is None:
            return []

        results: list[dict] = []
        seen: set[tuple[int, str]] = set()  # (id, relationship_type)

        # 1. Explicit links — both directions
        rows = self.conn.execute(
            "SELECT sl.link_type, sl.note, s.id, s.title, s.created_at, "
            "s.word_count, s.scene_count "
            "FROM script_links sl "
            "JOIN scripts s ON s.id = CASE "
            "  WHEN sl.source_script_id = ? THEN sl.target_script_id "
            "  ELSE sl.source_script_id END "
            "WHERE sl.source_script_id = ? OR sl.target_script_id = ?",
            (script_id, script_id, script_id),
        ).fetchall()
        for r in rows:
            key = (r["id"], "linked")
            if key not in seen:
                seen.add(key)
                results.append({
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "word_count": r["word_count"],
                    "scene_count": r["scene_count"],
                    "relationship_type": "linked",
                    "link_type": r["link_type"],
                    "note": r["note"],
                })

        # 2. Same category
        if script["selected_topic_json"] is not None:
            try:
                topic = json.loads(script["selected_topic_json"])
                category = topic.get("category")
            except (json.JSONDecodeError, TypeError):
                category = None

            if category is not None:
                cat_rows = self.conn.execute(
                    "SELECT id, title, created_at, word_count, scene_count "
                    "FROM scripts "
                    "WHERE id != ? "
                    "AND selected_topic_json IS NOT NULL "
                    "AND json_extract(selected_topic_json, '$.category') = ?",
                    (script_id, category),
                ).fetchall()
                for r in cat_rows:
                    key = (r["id"], "same_category")
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "id": r["id"],
                            "title": r["title"],
                            "created_at": r["created_at"],
                            "word_count": r["word_count"],
                            "scene_count": r["scene_count"],
                            "relationship_type": "same_category",
                        })

        # 3. Keyword overlap
        title_words = {
            w.lower()
            for w in script["title"].split()
            if len(w) > 2
        }
        if title_words:
            all_scripts = self.conn.execute(
                "SELECT id, title, created_at, word_count, scene_count "
                "FROM scripts WHERE id != ?",
                (script_id,),
            ).fetchall()
            for r in all_scripts:
                other_words = {w.lower() for w in r["title"].split()}
                if title_words & other_words:
                    key = (r["id"], "keyword_overlap")
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "id": r["id"],
                            "title": r["title"],
                            "created_at": r["created_at"],
                            "word_count": r["word_count"],
                            "scene_count": r["scene_count"],
                            "relationship_type": "keyword_overlap",
                        })

        return results

