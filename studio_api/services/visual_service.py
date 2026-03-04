"""Visual service — scene CRUD, footage search, single-scene render."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from studio_api.models.scene import FootageResult, SceneResponse, SceneUpdate
from studio_api.services.job_runner import JobRunner

logger = logging.getLogger(__name__)


class VisualService:
    """Manages scenes and wraps AssetOrchestrator + PexelsClient."""

    def __init__(self, conn: sqlite3.Connection, job_runner: JobRunner | None = None) -> None:
        self._conn = conn
        self._job_runner = job_runner

    def create_scenes_from_script(self, project_id: str, script_version_id: int) -> list[SceneResponse]:
        """Create scene rows from a finalized script's visual instructions."""
        row = self._conn.execute(
            "SELECT * FROM script_versions WHERE id = ? AND project_id = ?",
            (script_version_id, project_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"Script version {script_version_id} not found")

        script_json = json.loads(row["script_json"]) if isinstance(row["script_json"], str) else row["script_json"]
        scenes_data = script_json.get("scenes", [])
        now = datetime.now(timezone.utc).isoformat()
        created = []

        for scene in scenes_data:
            sn = scene.get("scene_number", 0)
            vi = scene.get("visual_instruction", {})
            vtype = vi.get("type", "text_overlay")
            vdata = vi.get("data", {})
            if "title" in vi:
                vdata["title"] = vi["title"]
            # Store narration text so the visual panel can show it
            narration = scene.get("narration_text", "")
            if narration:
                vdata["narration_text"] = narration
            transition = vi.get("transition", scene.get("transition", "fade"))

            cursor = self._conn.execute(
                "INSERT INTO scenes (project_id, scene_number, visual_type, visual_data_json, transition, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?)",
                (project_id, sn, vtype, json.dumps(vdata), transition, now, now),
            )
            created.append(self._get_scene(cursor.lastrowid))

        self._conn.commit()
        return created

    def list_scenes(self, project_id: str) -> list[SceneResponse]:
        rows = self._conn.execute(
            "SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number",
            (project_id,),
        ).fetchall()
        responses = [self._row_to_response(r, self._probe_duration(r["rendered_path"])) for r in rows]

        # Enrich scenes that are missing narration_text in visual_data
        # by falling back to audio_segments table
        missing = [r for r in responses if not (r.visual_data or {}).get("narration_text")]
        if missing:
            scene_numbers = [r.scene_number for r in missing]
            placeholders = ",".join("?" * len(scene_numbers))
            audio_rows = self._conn.execute(
                f"SELECT scene_number, narration_text FROM audio_segments "
                f"WHERE project_id = ? AND scene_number IN ({placeholders}) "
                f"ORDER BY version DESC",
                [project_id] + scene_numbers,
            ).fetchall()
            # Build map: scene_number -> narration_text (first match = latest version)
            narration_map: dict[int, str] = {}
            for ar in audio_rows:
                sn = ar["scene_number"]
                if sn not in narration_map:
                    narration_map[sn] = ar["narration_text"]
            for r in missing:
                text = narration_map.get(r.scene_number)
                if text:
                    if r.visual_data is None:
                        r.visual_data = {}
                    r.visual_data["narration_text"] = text

        return responses

    def get_scene(self, scene_id: int) -> SceneResponse | None:
        return self._get_scene(scene_id)

    def update_scene(self, scene_id: int, data: SceneUpdate) -> SceneResponse | None:
        existing = self._get_scene(scene_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        fields = ["updated_at = ?"]
        values = [now]

        if data.visual_type is not None:
            fields.append("visual_type = ?")
            values.append(data.visual_type)
        if data.visual_data is not None:
            fields.append("visual_data_json = ?")
            values.append(json.dumps(data.visual_data))
            # Reset status to PENDING when visual data changes on a rendered scene
            if existing.status == "RENDERED":
                fields.append("status = ?")
                values.append("PENDING")
        if data.stock_video_path is not None:
            fields.append("stock_video_path = ?")
            values.append(data.stock_video_path)
        if data.transition is not None:
            fields.append("transition = ?")
            values.append(data.transition)
        if data.effects is not None:
            fields.append("effects_json = ?")
            values.append(json.dumps(data.effects))
        if data.show_title is not None:
            fields.append("show_title = ?")
            values.append(1 if data.show_title else 0)
        if data.target_duration is not None:
            fields.append("target_duration = ?")
            values.append(data.target_duration)
        if data.clip_count is not None:
            fields.append("clip_count = ?")
            values.append(data.clip_count)

        values.append(scene_id)
        self._conn.execute(
            f"UPDATE scenes SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return self._get_scene(scene_id)

    def suggest_keywords(self, project_id: str, scene_id: int) -> "SuggestionResponse":
        """Load scene + neighbors, call KeywordResearcher, return suggestions.

        Raises ValueError if scene not found or not a stock type.
        """
        from asset_orchestrator.keyword_researcher import KeywordResearcher, SuggestionResponse

        # Load and validate target scene
        scene = self._get_scene(scene_id)
        if scene is None:
            raise ValueError(f"Scene {scene_id} not found")

        STOCK_VISUAL_TYPES = {"stock_video", "stock_with_text", "stock_with_stat", "stock_quote"}
        if scene.visual_type not in STOCK_VISUAL_TYPES:
            raise ValueError(
                f"Keyword suggestions are only available for stock footage scenes, got '{scene.visual_type}'"
            )

        # Load all project scenes to find neighbors
        all_scenes = self.list_scenes(project_id)
        sorted_scenes = sorted(all_scenes, key=lambda s: s.scene_number)
        target_idx = next((i for i, s in enumerate(sorted_scenes) if s.id == scene_id), None)

        # Extract narration from target and neighbors
        def get_narration(s) -> str:
            vd = s.visual_data or {}
            return vd.get("narration_text", "")

        narration = get_narration(sorted_scenes[target_idx])
        prev_narration = get_narration(sorted_scenes[target_idx - 1]) if target_idx > 0 else None
        next_narration = (
            get_narration(sorted_scenes[target_idx + 1])
            if target_idx < len(sorted_scenes) - 1
            else None
        )

        researcher = KeywordResearcher()
        return researcher.research(narration, prev_narration, next_narration)


    @staticmethod
    def _refine_search_queries(query: str) -> list[str]:
        """Turn a technical query into 2-3 visual-friendly stock search terms.

        Stock APIs (Pexels/Pixabay) work best with simple, concrete visual
        concepts — not technical jargon.  We use GPT-4o-mini to produce
        alternative queries, falling back to simple word splitting.
        """
        import os
        queries = [query]  # always include original

        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": (
                            "You are a stock footage search assistant. "
                            "Given a search query for B-roll video, produce 2 alternative "
                            "search phrases that a stock video site would match well. "
                            "Focus on concrete visual concepts (objects, actions, places, "
                            "abstract visuals). Keep each phrase 1-3 words. "
                            "Return ONLY a newline-separated list, nothing else.\n\n"
                            f"Query: {query}"
                        ),
                    }],
                    max_tokens=40,
                    temperature=0.4,
                )
                raw = resp.choices[0].message.content.strip()
                for line in raw.splitlines():
                    term = line.strip().strip("-•").strip()
                    if term and term.lower() != query.lower():
                        queries.append(term)
            except Exception as exc:
                logger.debug("LLM query refinement failed: %s", exc)

        # Fallback: if LLM didn't add anything, split long queries
        if len(queries) == 1 and len(query.split()) > 2:
            words = query.split()
            queries.append(" ".join(words[:2]))
            if len(words) > 3:
                queries.append(" ".join(words[-2:]))

        return queries[:3]

    def search_footage(self, query: str) -> list[FootageResult]:
        """Search Pexels for footage — uses query refinement for better results."""
        try:
            from asset_orchestrator.pexels_client import PexelsClient
            client = PexelsClient()

            queries = self._refine_search_queries(query)
            seen_ids: set[int] = set()
            out: list[FootageResult] = []

            for q in queries:
                per_page = 15 if q == query else 8
                results = client.search_videos(q, per_page=per_page, min_duration=1)
                for r in results:
                    if r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    preview_url = ""
                    video_files = r.get("video_files", [])
                    for vf in sorted(video_files, key=lambda f: f.get("height", 0)):
                        if vf.get("link"):
                            preview_url = vf["link"]
                            break
                    out.append(FootageResult(
                        video_id=r["id"],
                        url=r["url"],
                        preview_url=preview_url,
                        duration=r["duration"],
                        width=r["width"],
                        height=r["height"],
                    ))
            return out
        except Exception as e:
            logger.error("Pexels search failed: %s", e)
            return []

    def search_wikimedia(self, query: str) -> list:
        """Search Wikimedia Commons — uses query refinement for better results."""
        from studio_api.models.scene import WikimediaImageResult
        try:
            from asset_orchestrator.wikimedia_client import WikimediaCommonsClient
            client = WikimediaCommonsClient()

            queries = self._refine_search_queries(query)
            seen_urls: set[str] = set()
            out: list[WikimediaImageResult] = []

            for q in queries:
                limit = 20 if q == query else 10
                results = client.search_images(q, limit=limit, min_width=640)
                for r in results:
                    if r.url in seen_urls:
                        continue
                    seen_urls.add(r.url)
                    out.append(WikimediaImageResult(
                        title=r.title,
                        url=r.url,
                        thumb_url=r.thumb_url,
                        width=r.width,
                        height=r.height,
                        license=r.license,
                        attribution=r.attribution,
                    ))
            return out
        except Exception as e:
            logger.error("Wikimedia search failed: %s", e)
            return []
    def search_pixabay(self, query: str) -> list:
        """Search Pixabay for stock videos — uses query refinement for better results."""
        from studio_api.models.scene import PixabayVideoResult
        try:
            from asset_orchestrator.pixabay_client import PixabayClient
            client = PixabayClient()

            queries = self._refine_search_queries(query)
            seen_ids: set[int] = set()
            out: list[PixabayVideoResult] = []

            for q in queries:
                per_page = 10 if q == query else 6
                results = client.search_videos(q, per_page=per_page, min_duration=1)
                for r in results:
                    if r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    out.append(PixabayVideoResult(
                        video_id=r["id"],
                        url=r.get("url", ""),
                        preview_url=r.get("download_url", ""),
                        duration=r.get("duration", 0),
                        width=r.get("width", 0),
                        height=r.get("height", 0),
                        tags=r.get("tags", ""),
                    ))
            return out
        except Exception as e:
            logger.error("Pixabay search failed: %s", e)
            return []
    def search_all_sources(self, query: str) -> list[dict]:
        """Search Pexels + Pixabay + Wikimedia + Unsplash and return merged results.

        Each result dict has a `_source` field so the frontend knows the origin.
        """
        combined: list[dict] = []

        for r in self.search_footage(query):
            combined.append({
                "_source": "pexels",
                "video_id": r.video_id,
                "url": r.url,
                "preview_url": r.preview_url,
                "duration": r.duration,
                "width": r.width,
                "height": r.height,
            })

        for r in self.search_pixabay(query):
            combined.append({
                "_source": "pixabay",
                "video_id": r.video_id,
                "url": r.url,
                "preview_url": r.preview_url,
                "duration": r.duration,
                "width": r.width,
                "height": r.height,
                "tags": r.tags,
            })

        for r in self.search_wikimedia(query):
            combined.append({
                "_source": "wikimedia",
                "title": r.title,
                "url": r.url,
                "thumb_url": r.thumb_url,
                "width": r.width,
                "height": r.height,
                "license": r.license,
                "attribution": r.attribution,
            })

        for r in self.search_unsplash(query):
            combined.append({
                "_source": "unsplash",
                "photo_id": r.photo_id,
                "url": r.url,
                "thumb_url": r.thumb_url,
                "page_url": r.page_url,
                "width": r.width,
                "height": r.height,
                "description": r.description,
                "photographer": r.photographer,
            })

        return combined
    def search_unsplash(self, query: str) -> list:
        """Search Unsplash for high-quality stock photos."""
        from studio_api.models.scene import UnsplashPhotoResult
        try:
            from asset_orchestrator.unsplash_client import UnsplashClient
            client = UnsplashClient()

            queries = self._refine_search_queries(query)
            seen_ids: set[str] = set()
            out: list[UnsplashPhotoResult] = []

            for q in queries:
                per_page = 15 if q == query else 8
                results = client.search_photos(q, per_page=per_page)
                for r in results:
                    if r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    out.append(UnsplashPhotoResult(
                        photo_id=r["id"],
                        url=r.get("url", ""),
                        thumb_url=r.get("thumb_url", ""),
                        page_url=r.get("page_url", ""),
                        width=r.get("width", 0),
                        height=r.get("height", 0),
                        description=r.get("description", ""),
                        photographer=r.get("photographer", ""),
                    ))
            return out
        except Exception as e:
            logger.error("Unsplash search failed: %s", e)
            return []

    def render_scene(self, project_id: str, scene_id: int) -> dict:
        """Render a single scene via AssetOrchestrator.

        All scene types are routed through the Pexels stock footage pipeline
        for production-quality YouTube output. Non-stock types (text_overlay,
        reddit_post, bullet_reveal, etc.) are mapped to stock_with_text with
        auto-generated keywords from the scene data.
        """
        if self._job_runner is None:
            raise RuntimeError("JobRunner not configured")

        scene = self._get_scene(scene_id)
        if scene is None:
            raise ValueError(f"Scene {scene_id} not found")

        job = self._job_runner.create_job(project_id, "render_scene", input_data={"scene_id": scene_id})
        self._job_runner.start_job(job.id)
        try:
            # Delete old rendered file so re-render produces a fresh output
            if scene.rendered_path:
                self._cleanup_scene_files(scene.rendered_path)
                self._conn.execute(
                    "UPDATE scenes SET rendered_path = NULL WHERE id = ?", (scene_id,),
                )
                self._conn.commit()

            from asset_orchestrator.orchestrator import AssetOrchestrator, STOCK_SCENE_TYPES
            orch = AssetOrchestrator()

            vtype = scene.visual_type
            vdata = dict(scene.visual_data) if scene.visual_data else {}
            title = vdata.get("title", f"Scene {scene.scene_number}")

            # Map non-stock types to stock equivalents for Pexels rendering
            if vtype not in STOCK_SCENE_TYPES and vtype != "data_chart":
                # reddit_post → social_card (styled UI mockup)
                if vtype == "reddit_post":
                    vtype = "social_card"
                    vdata.setdefault("platform", "reddit")
                    vdata.setdefault("username", vdata.get("author", "u/anonymous"))
                    if not vdata.get("keywords"):
                        vdata["keywords"] = ["dark abstract technology"]
                    logger.info("Scene %d: mapped reddit_post → social_card", scene.scene_number)
                else:
                    # Everything else → stock_with_text
                    heading = (
                        vdata.get("heading")
                        or vdata.get("post_title")
                        or vdata.get("quote")
                        or vdata.get("value")
                        or title
                    )
                    body = (
                        vdata.get("body")
                        or vdata.get("subtitle")
                        or vdata.get("attribution")
                        or vdata.get("label")
                        or ""
                    )
                    keywords = vdata.get("keywords", [])
                    if not keywords:
                        words = f"{title} {heading}".split()
                        keywords = [w for w in words if len(w) > 3][:3] or ["technology"]

                    vtype = "stock_with_text"
                    vdata = {
                        "heading": heading,
                        "body": body,
                        "keywords": keywords,
                        "title": title,
                    }
                    # Preserve source flag (e.g. "wikimedia") if user selected footage
                    if scene.visual_data and scene.visual_data.get("source"):
                        vdata["source"] = scene.visual_data["source"]
                    if scene.visual_data and scene.visual_data.get("wikimedia_attribution"):
                        vdata["wikimedia_attribution"] = scene.visual_data["wikimedia_attribution"]
                    logger.info("Scene %d: mapped %s → stock_with_text (keywords=%s)",
                                scene.scene_number, scene.visual_type, keywords)

            # Also fetch narration text and actual audio duration for this scene
            narration_text = None
            audio_duration = None
            seg_row = self._conn.execute(
                "SELECT narration_text, audio_file_path, start_time, end_time, status "
                "FROM audio_segments WHERE project_id = ? AND scene_number = ? "
                "ORDER BY version DESC LIMIT 1",
                (project_id, scene.scene_number),
            ).fetchone()
            if seg_row:
                narration_text = seg_row["narration_text"]
                # If audio has been synthesized/uploaded, get actual duration
                if seg_row["status"] in ("SYNTHESIZED", "UPLOADED") and seg_row["audio_file_path"]:
                    audio_path = seg_row["audio_file_path"]
                    import os as _os
                    if _os.path.isfile(audio_path):
                        # Try to get actual file duration via ffprobe
                        try:
                            import subprocess
                            probe = subprocess.run(
                                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                                capture_output=True, text=True, timeout=10,
                            )
                            if probe.returncode == 0 and probe.stdout.strip():
                                audio_duration = float(probe.stdout.strip())
                                logger.info("Scene %d: actual audio duration = %.2fs (from %s)",
                                            scene.scene_number, audio_duration, audio_path)
                        except Exception as e:
                            logger.warning("Scene %d: ffprobe failed: %s", scene.scene_number, e)
                    else:
                        logger.warning("Scene %d: audio file missing: %s", scene.scene_number, audio_path)
                
                # Fallback: if audio not synthesized yet, estimate from SRT times
                if audio_duration is None and seg_row["start_time"] and seg_row["end_time"]:
                    try:
                        # Parse SRT timestamps (HH:MM:SS,mmm)
                        def parse_srt(ts: str) -> float:
                            h, m, s = ts.replace(',', '.').split(':')
                            return float(h) * 3600 + float(m) * 60 + float(s)
                        audio_duration = parse_srt(seg_row["end_time"]) - parse_srt(seg_row["start_time"])
                        logger.info("Scene %d: estimated audio duration from SRT = %.1fs",
                                    scene.scene_number, audio_duration)
                    except Exception:
                        pass

            final_target = audio_duration or scene.target_duration
            logger.info("Scene %d: target_duration=%.2fs (audio=%.2fs, scene.target=%s)",
                        scene.scene_number,
                        final_target or 0,
                        audio_duration or 0,
                        scene.target_duration)
            instruction = {
                "type": vtype,
                "title": title,
                "data": vdata,
                "scene_number": scene.scene_number,
                "effects": scene.effects,
                "show_title": scene.show_title,
                "target_duration": final_target,
                "clip_count": scene.clip_count,
            }
            result = orch.process_instruction(instruction, narration_text=narration_text)

            if result.get("status") == "error":
                raise RuntimeError(result.get("error", "Render failed"))

            rendered_path = result.get("output_path", "")

            # Persist auto-generated clips back so the UI shows what was used
            clips_used = result.get("clips_used")
            if clips_used:
                current_vdata = dict(scene.visual_data) if scene.visual_data else {}
                if not current_vdata.get("clips"):
                    current_vdata["clips"] = clips_used
                    self._conn.execute(
                        "UPDATE scenes SET visual_data_json = ? WHERE id = ?",
                        (json.dumps(current_vdata), scene_id),
                    )

            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                "UPDATE scenes SET rendered_path = ?, status = 'RENDERED', updated_at = ? WHERE id = ?",
                (rendered_path, now, scene_id),
            )
            self._conn.commit()
            self._job_runner.complete_job(job.id, output_data={"rendered_path": rendered_path})
            return {"job_id": job.id, "rendered_path": rendered_path}
        except Exception as e:
            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                "UPDATE scenes SET status = 'FAILED', updated_at = ? WHERE id = ?",
                (now, scene_id),
            )
            self._conn.commit()
            self._job_runner.fail_job(job.id, str(e))
            raise
    def delete_all_scenes(self, project_id: str) -> int:
        """Delete all scenes for a project. Cleans up rendered files on disk."""
        rows = self._conn.execute(
            "SELECT rendered_path, stock_video_path FROM scenes WHERE project_id = ?",
            (project_id,),
        ).fetchall()
        for row in rows:
            self._cleanup_scene_files(row["rendered_path"], row["stock_video_path"])

        cursor = self._conn.execute(
            "DELETE FROM scenes WHERE project_id = ?", (project_id,)
        )
        self._conn.commit()
        return cursor.rowcount
    def add_scene(self, project_id: str, data: "SceneCreate") -> SceneResponse:
        """Add a new blank scene at the end of the project's scene list."""
        from studio_api.models.scene import SceneCreate  # noqa: F811

        # Determine next scene_number
        row = self._conn.execute(
            "SELECT COALESCE(MAX(scene_number), 0) AS mx FROM scenes WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        next_num = row["mx"] + 1

        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "INSERT INTO scenes (project_id, scene_number, visual_type, visual_data_json, "
            "target_duration, clip_count, transition, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'fade', 'PENDING', ?, ?)",
            (project_id, next_num, data.visual_type, json.dumps(data.visual_data),
             data.target_duration, data.clip_count, now, now),
        )
        self._conn.commit()
        return self._get_scene(cursor.lastrowid)  # type: ignore[return-value]

    def delete_scene(self, scene_id: int) -> bool:
        """Delete a single scene and clean up its files on disk."""
        row = self._conn.execute(
            "SELECT rendered_path, stock_video_path FROM scenes WHERE id = ?",
            (scene_id,),
        ).fetchone()
        if row:
            self._cleanup_scene_files(row["rendered_path"], row["stock_video_path"])
        cursor = self._conn.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
        self._conn.commit()
        return cursor.rowcount > 0



    def _get_scene(self, scene_id: int) -> SceneResponse | None:
        row = self._conn.execute(
            "SELECT * FROM scenes WHERE id = ?", (scene_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row, self._probe_duration(row["rendered_path"]))

    @staticmethod
    def _cleanup_scene_files(*paths: str | None) -> None:
        """Best-effort delete of rendered/composed files on disk."""
        import os
        for path in paths:
            if not path:
                continue
            try:
                abspath = os.path.abspath(path)
                if os.path.isfile(abspath):
                    os.unlink(abspath)
                    logger.info("Deleted scene file: %s", abspath)
            except Exception as exc:
                logger.warning("Failed to delete %s: %s", path, exc)

    @staticmethod
    def clear_stock_cache() -> dict:
        """Remove all cached stock footage downloads to force fresh fetches.

        Returns dict with per-directory counts of files removed.
        """
        import os
        import shutil

        cache_dirs = [
            "output/stock_cache",
            "output/pixabay_cache",
            "output/wikimedia_cache",
            "output/composed_stock",
        ]
        result: dict[str, int] = {}
        for d in cache_dirs:
            absd = os.path.abspath(d)
            if not os.path.isdir(absd):
                result[d] = 0
                continue
            count = 0
            for f in os.listdir(absd):
                fp = os.path.join(absd, f)
                try:
                    if os.path.isfile(fp):
                        os.unlink(fp)
                        count += 1
                except Exception as exc:
                    logger.warning("Failed to delete cache file %s: %s", fp, exc)
            result[d] = count
        return result

    @staticmethod
    def _probe_duration(path: str | None) -> float | None:
        """Return duration in seconds for a rendered video file, or None."""
        if not path:
            return None
        import os
        import subprocess
        if not os.path.isfile(path):
            return None
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True, timeout=5,
            )
            return round(float(probe.stdout.strip()), 2) if probe.stdout.strip() else None
        except Exception:
            return None

    @staticmethod
    def _row_to_response(row: sqlite3.Row, duration: float | None = None) -> SceneResponse:
        vdata = row["visual_data_json"]
        if isinstance(vdata, str):
            try:
                vdata = json.loads(vdata)
            except json.JSONDecodeError:
                vdata = {}
        effects_raw = row["effects_json"] if "effects_json" in row.keys() else "[]"
        if isinstance(effects_raw, str):
            try:
                effects = json.loads(effects_raw)
            except json.JSONDecodeError:
                effects = []
        else:
            effects = effects_raw or []
        return SceneResponse(
            id=row["id"],
            project_id=row["project_id"],
            scene_number=row["scene_number"],
            visual_type=row["visual_type"],
            visual_data=vdata,
            stock_video_path=row["stock_video_path"],
            rendered_path=row["rendered_path"],
            thumbnail_path=row["thumbnail_path"],
            transition=row["transition"] if "transition" in row.keys() else "fade",
            effects=effects,
            show_title=bool(row["show_title"]) if "show_title" in row.keys() else False,
            target_duration=row["target_duration"] if "target_duration" in row.keys() else None,
            clip_count=row["clip_count"] if "clip_count" in row.keys() else 0,
            duration=duration,
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
