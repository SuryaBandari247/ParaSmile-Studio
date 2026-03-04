"""Script service — version management, conversion, finalization, diff."""

from __future__ import annotations

import difflib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from studio_api.models.script import (
    DiffResult,
    ScriptVersionCreate,
    ScriptVersionResponse,
    ScriptVersionUpdate,
)

logger = logging.getLogger(__name__)


class ScriptService:
    """Manages script versions within a project scope."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def generate_from_raw(self, project_id: str, topic_id: str, title: str, raw_text: str) -> ScriptVersionResponse:
        """Use ScriptConverter to split raw text into scenes, then save as a new version."""
        from script_generator.converter import ScriptConverter

        converter = ScriptConverter()
        video_script = converter.convert(raw_text)

        # Convert VideoScript scenes to our JSON format
        scenes = []
        for scene in video_script.scenes:
            scene_data: dict = {
                "scene_number": scene.scene_number,
                "narration": scene.narration_text,
                "narration_text": scene.narration_text,
                "emotion": scene.emotion,
                "visual_type": scene.visual_instruction.get("type", "text_overlay"),
                "visual_instruction": scene.visual_instruction,
            }
            scenes.append(scene_data)

        script_json = {
            "title": video_script.title,
            "scenes": scenes,
            "total_word_count": video_script.total_word_count,
            "generated_at": video_script.generated_at.isoformat() if hasattr(video_script.generated_at, 'isoformat') else str(video_script.generated_at),
        }

        data = ScriptVersionCreate(topic_id=topic_id, title=title, script_json=script_json)
        return self.create(project_id, data)
    def import_json(self, project_id: str, script_json: dict, title: str | None = None) -> ScriptVersionResponse:
        """Import a pre-built script JSON directly, auto-finalize it.

        This bypasses the LLM entirely — the JSON is stored as-is, preserving
        all visual_instruction fields exactly as authored.

        Each import creates its own topic so the dashboard card shows the
        actual script title instead of a generic "Imported Scripts" label.
        """
        if "scenes" not in script_json:
            raise ValueError("script_json must contain a 'scenes' array")

        resolved_title = title or script_json.get("title", "Imported Script")

        # Create a dedicated topic for this import so the title shows correctly
        from studio_api.models.topic import TopicCreate, TopicStatus, TopicUpdate
        from studio_api.services.topic_service import TopicService

        topic_svc = TopicService(self._conn)
        topic = topic_svc.create(project_id, TopicCreate(
            title=resolved_title,
            source="import",
        ))
        # Auto-select so it's immediately visible in the pipeline
        topic_svc.update(topic.id, TopicUpdate(status=TopicStatus.SELECTED))

        data = ScriptVersionCreate(
            topic_id=topic.id,
            title=resolved_title,
            script_json=script_json,
        )
        version = self.create(project_id, data)
        # Auto-finalize so it's immediately usable in the Visuals panel
        return self.finalize(version.id)

    def create(self, project_id: str, data: ScriptVersionCreate) -> ScriptVersionResponse:
        """Create a new script version (auto-increments version number)."""
        version = self._next_version(project_id, data.topic_id)
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "INSERT INTO script_versions (project_id, topic_id, version, title, script_json, is_finalized, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (project_id, data.topic_id, version, data.title,
             json.dumps(data.script_json), now),
        )
        self._conn.commit()
        return self.get(cursor.lastrowid)

    def get(self, version_id: int) -> ScriptVersionResponse | None:
        row = self._conn.execute(
            "SELECT * FROM script_versions WHERE id = ?", (version_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    def list_for_project(self, project_id: str) -> list[ScriptVersionResponse]:
        rows = self._conn.execute(
            "SELECT * FROM script_versions WHERE project_id = ? ORDER BY id DESC",
            (project_id,),
        ).fetchall()
        return [self._row_to_response(r) for r in rows]

    def update(self, version_id: int, data: ScriptVersionUpdate) -> ScriptVersionResponse | None:
        existing = self.get(version_id)
        if existing is None:
            return None
        if existing.is_finalized:
            raise ValueError("Cannot update a finalized script version")

        fields = []
        values = []
        if data.title is not None:
            fields.append("title = ?")
            values.append(data.title)
        if data.script_json is not None:
            fields.append("script_json = ?")
            values.append(json.dumps(data.script_json))

        if not fields:
            return existing

        values.append(version_id)
        self._conn.execute(
            f"UPDATE script_versions SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return self.get(version_id)

    def finalize(self, version_id: int) -> ScriptVersionResponse | None:
        existing = self.get(version_id)
        if existing is None:
            return None
        if existing.is_finalized:
            return existing  # idempotent
        self._conn.execute(
            "UPDATE script_versions SET is_finalized = 1 WHERE id = ?",
            (version_id,),
        )
        self._conn.commit()
        return self.get(version_id)

    def enrich_keywords(self, version_id: int) -> ScriptVersionResponse | None:
        """Run keyword research on all stock scenes in a script version.

        This is an opt-in operation triggered by the user. It enriches each
        stock scene's visual_instruction.data with researched keywords,
        source-specific hints, categorized keyword map, and narrative beats.
        Scenes that already have keywords are re-researched (user explicitly
        asked for enrichment).
        """
        existing = self.get(version_id)
        if existing is None:
            return None

        enriched_json = self._enrich_script_keywords(existing.script_json)
        if enriched_json != existing.script_json:
            self._conn.execute(
                "UPDATE script_versions SET script_json = ? WHERE id = ?",
                (json.dumps(enriched_json), version_id),
            )
            self._conn.commit()

        return self.get(version_id)

    def _enrich_script_keywords(self, script_json: dict) -> dict:
        """Run KeywordResearcher on each stock scene to populate keywords and keyword_research.

        Analyzes narration context (prev/next scenes) to produce categorized
        keyword maps, source-specific hints, and narrative beats. Skips scenes
        that already have keywords populated.
        """
        scenes = script_json.get("scenes", [])
        if not scenes:
            return script_json

        STOCK_TYPES = {"stock_video", "stock_with_text", "stock_with_stat", "stock_quote"}

        try:
            from asset_orchestrator.keyword_researcher import KeywordResearcher
            researcher = KeywordResearcher()
        except Exception as exc:
            logger.warning("KeywordResearcher unavailable, skipping enrichment: %s", exc)
            return script_json

        enriched_scenes = list(scenes)
        for i, scene in enumerate(enriched_scenes):
            vi = scene.get("visual_instruction", {})
            vtype = vi.get("type", scene.get("visual_type", ""))
            vdata = vi.get("data", {})

            # Skip non-stock scenes
            if vtype not in STOCK_TYPES:
                continue

            narration = scene.get("narration_text", scene.get("narration", ""))
            if not narration:
                continue

            prev_narration = None
            next_narration = None
            if i > 0:
                prev_narration = enriched_scenes[i - 1].get("narration_text", enriched_scenes[i - 1].get("narration", ""))
            if i < len(enriched_scenes) - 1:
                next_narration = enriched_scenes[i + 1].get("narration_text", enriched_scenes[i + 1].get("narration", ""))

            try:
                result = researcher.research(narration, prev_narration, next_narration)

                # Store individual keywords (not joined)
                vdata["keywords"] = [s.keyword for s in result.suggestions]

                # Store full research data for the orchestrator to use source hints
                vdata["keyword_research"] = result.model_dump()

                vi["data"] = vdata
                scene["visual_instruction"] = vi
                enriched_scenes[i] = scene

                logger.info(
                    "Scene %d: enriched with %d keywords, %d beats",
                    scene.get("scene_number", i),
                    len(result.suggestions),
                    len(result.narrative_beats),
                )
            except Exception as exc:
                logger.warning("Keyword research failed for scene %d: %s", scene.get("scene_number", i), exc)

        enriched = dict(script_json)
        enriched["scenes"] = enriched_scenes
        return enriched
    def delete_all(self, project_id: str) -> int:
        """Delete all script versions for a project. Returns count deleted.

        Also removes related audio_segments to avoid foreign key violations.
        """
        # Delete audio segments that reference this project's script versions
        self._conn.execute(
            "DELETE FROM audio_segments WHERE script_version_id IN "
            "(SELECT id FROM script_versions WHERE project_id = ?)",
            (project_id,),
        )
        cursor = self._conn.execute(
            "DELETE FROM script_versions WHERE project_id = ?", (project_id,)
        )
        self._conn.commit()
        return cursor.rowcount

    def diff(self, version_id_a: int, version_id_b: int) -> DiffResult | None:
        a = self.get(version_id_a)
        b = self.get(version_id_b)
        if a is None or b is None:
            return None

        a_lines = json.dumps(a.script_json, indent=2).splitlines(keepends=True)
        b_lines = json.dumps(b.script_json, indent=2).splitlines(keepends=True)
        diff = list(difflib.unified_diff(a_lines, b_lines, fromfile=f"v{a.version}", tofile=f"v{b.version}"))

        changes = []
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                changes.append({"type": "added", "content": line.rstrip()})
            elif line.startswith("-") and not line.startswith("---"):
                changes.append({"type": "removed", "content": line.rstrip()})

        return DiffResult(version_a=a.version, version_b=b.version, changes=changes)

    def _next_version(self, project_id: str, topic_id: str) -> int:
        # Version numbers are global within a project so that multiple
        # imports (each with their own topic) still get incrementing versions.
        row = self._conn.execute(
            "SELECT MAX(version) as max_v FROM script_versions WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        current = row["max_v"] if row and row["max_v"] is not None else 0
        return current + 1

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> ScriptVersionResponse:
        script_json = row["script_json"]
        if isinstance(script_json, str):
            try:
                script_json = json.loads(script_json)
            except json.JSONDecodeError:
                script_json = {}
        return ScriptVersionResponse(
            id=row["id"],
            project_id=row["project_id"],
            topic_id=row["topic_id"],
            version=row["version"],
            title=row["title"],
            script_json=script_json,
            is_finalized=bool(row["is_finalized"]),
            created_at=row["created_at"],
        )
