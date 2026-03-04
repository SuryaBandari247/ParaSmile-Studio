"""Render service — final video composition, scene ordering, music mixing."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from studio_api.models.scene import MusicSettings
from studio_api.services.job_runner import JobRunner

logger = logging.getLogger(__name__)


class RenderService:
    """Manages final render composition and scene ordering."""

    def __init__(self, conn: sqlite3.Connection, job_runner: JobRunner | None = None) -> None:
        self._conn = conn
        self._job_runner = job_runner

    def get_scene_order(self, project_id: str) -> list[dict]:
        """Get current scene order for a project."""
        rows = self._conn.execute(
            "SELECT id, scene_number, visual_type, status, rendered_path, thumbnail_path "
            "FROM scenes WHERE project_id = ? ORDER BY scene_number",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def reorder_scenes(self, project_id: str, scene_ids: list[int]) -> list[dict]:
        """Update scene_number based on the provided order of scene IDs."""
        now = datetime.now(timezone.utc).isoformat()
        for idx, scene_id in enumerate(scene_ids, start=1):
            self._conn.execute(
                "UPDATE scenes SET scene_number = ?, updated_at = ? WHERE id = ? AND project_id = ?",
                (idx, now, scene_id, project_id),
            )
        self._conn.commit()
        return self.get_scene_order(project_id)

    def upload_music(self, project_id: str, filename: str, data: bytes) -> dict:
        """Store uploaded music file for the project."""
        from studio_api.services.artifact_store import ArtifactStore
        store = ArtifactStore(self._conn)
        return store.store(project_id, "music_file", filename, data)

    def update_music_settings(self, project_id: str, settings: MusicSettings) -> dict:
        """Store music settings as project metadata."""
        # Store as a simple artifact with settings in metadata
        from studio_api.services.artifact_store import ArtifactStore
        store = ArtifactStore(self._conn)
        return store.store(
            project_id, "music_settings", "settings.json",
            json.dumps(settings.model_dump()).encode(),
            metadata=settings.model_dump(),
        )

    def start_render(self, project_id: str) -> dict:
        """Start final video render — concat all rendered scenes with xfade transitions."""
        if self._job_runner is None:
            raise RuntimeError("JobRunner not configured")

        job = self._job_runner.create_job(project_id, "render_final")
        self._job_runner.start_job(job.id)
        try:
            import os
            import subprocess
            import uuid

            scenes = self._conn.execute(
                "SELECT id, scene_number, rendered_path, transition "
                "FROM scenes WHERE project_id = ? ORDER BY scene_number",
                (project_id,),
            ).fetchall()
            rendered = [dict(s) for s in scenes if s["rendered_path"] and os.path.isfile(s["rendered_path"])]
            if not rendered:
                raise ValueError("No rendered scenes available for final composition")

            output_dir = os.path.abspath(f"output/final/{project_id}")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"final_{uuid.uuid4().hex[:8]}.mp4")

            xfade_dur = 0.5

            if len(rendered) == 1:
                # Single scene — just copy
                import shutil
                shutil.copy2(rendered[0]["rendered_path"], output_path)
            else:
                # Build xfade filter chain
                # Get durations of each clip
                durations = []
                for s in rendered:
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", s["rendered_path"]],
                        capture_output=True, text=True,
                    )
                    dur = float(probe.stdout.strip()) if probe.stdout.strip() else 8.0
                    durations.append(dur)

                # Build inputs
                inputs = []
                for s in rendered:
                    inputs += ["-i", s["rendered_path"]]

                # Build xfade filter chain
                # Each xfade takes two streams and produces one
                # offset = cumulative duration - cumulative xfade overlaps
                filter_parts = []
                cumulative = durations[0]

                for i in range(1, len(rendered)):
                    transition = rendered[i].get("transition", "fade") or "fade"
                    if transition == "none":
                        transition = "fade"
                        xfade_d = 0.01  # near-instant
                    else:
                        xfade_d = xfade_dur

                    offset = cumulative - xfade_d
                    if offset < 0:
                        offset = 0

                    if i == 1:
                        src_a = "[0:v]"
                        src_b = "[1:v]"
                    else:
                        src_a = f"[vfade{i-1}]"
                        src_b = f"[{i}:v]"

                    out_label = f"[vfade{i}]" if i < len(rendered) - 1 else "[vout]"
                    filter_parts.append(
                        f"{src_a}{src_b}xfade=transition={transition}:duration={xfade_d:.3f}:offset={offset:.3f}{out_label}"
                    )
                    cumulative = offset + durations[i]

                filter_str = ";".join(filter_parts)

                cmd = inputs.copy()
                cmd = ["ffmpeg", "-y"] + cmd
                cmd += ["-filter_complex", filter_str]
                cmd += ["-map", "[vout]"]
                cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30"]
                cmd += [output_path]

                logger.info("Final render with transitions: %s", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")

            # Mix in per-scene narration audio (from Audio panel)
            narration_audio = self._build_narration_track(
                project_id, rendered, output_dir, xfade_dur=xfade_dur
            )
            if narration_audio and os.path.isfile(narration_audio):
                narrated_path = os.path.join(output_dir, f"final_narrated_{uuid.uuid4().hex[:8]}.mp4")
                cmd_narrate = [
                    "ffmpeg", "-y",
                    "-i", output_path,
                    "-i", narration_audio,
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac",
                    narrated_path,
                ]
                logger.info("Mixing narration audio: %s", " ".join(cmd_narrate))
                nar_result = subprocess.run(cmd_narrate, capture_output=True, text=True)
                if nar_result.returncode == 0:
                    output_path = narrated_path
                else:
                    logger.warning("Narration mix failed: %s", nar_result.stderr[:300])

            # Check if there's background music to mix in
            music_path = self._get_music_path(project_id)
            if music_path and os.path.isfile(music_path):
                settings = self._get_music_settings(project_id)
                vol = settings.get("volume", 80) / 100.0
                fade_in_s = settings.get("fade_in_ms", 1000) / 1000.0
                fade_out_s = settings.get("fade_out_ms", 2000) / 1000.0

                mixed_path = os.path.join(output_dir, f"final_mixed_{uuid.uuid4().hex[:8]}.mp4")
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", output_path],
                    capture_output=True, text=True,
                )
                vid_dur = float(probe.stdout.strip()) if probe.stdout.strip() else 60.0
                fade_out_start = max(0, vid_dur - fade_out_s)

                # Check if video already has an audio stream (narration)
                has_audio = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "a",
                     "-show_entries", "stream=index", "-of", "csv=p=0", output_path],
                    capture_output=True, text=True,
                )
                has_existing_audio = bool(has_audio.stdout.strip())

                music_filter = (
                    f"[{2 if has_existing_audio else 1}:a]volume={vol:.2f},"
                    f"afade=t=in:st=0:d={fade_in_s:.1f},"
                    f"afade=t=out:st={fade_out_start:.1f}:d={fade_out_s:.1f},"
                    f"apad,atrim=0:{vid_dur:.2f}[music]"
                )

                if has_existing_audio:
                    # Mix narration (0:a) + music together
                    music_filter += ";[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                    map_audio = ["-map", "[aout]"]
                else:
                    music_filter += ";[music]anull[aout]"
                    map_audio = ["-map", "[aout]"]

                cmd_mix = [
                    "ffmpeg", "-y",
                    "-i", output_path,
                    "-i", music_path,
                    "-filter_complex", music_filter,
                    "-map", "0:v", *map_audio,
                    "-c:v", "copy", "-c:a", "aac", "-shortest",
                    mixed_path,
                ]
                mix_result = subprocess.run(cmd_mix, capture_output=True, text=True)
                if mix_result.returncode == 0:
                    output_path = mixed_path

            output_data = {
                "scene_count": len(rendered),
                "output_path": output_path,
            }
            self._job_runner.complete_job(job.id, output_data=output_data)
            return {"job_id": job.id, "status": "COMPLETED", "output": output_data}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def get_final_output_path(self, project_id: str) -> str | None:
        """Get the output path of the latest completed final render."""
        status = self.get_render_status(project_id)
        if status and status.get("status") == "COMPLETED" and status.get("output"):
            return status["output"].get("output_path")
        return None

    def _get_music_path(self, project_id: str) -> str | None:
        """Get the stored music file path for a project."""
        row = self._conn.execute(
            "SELECT file_path FROM artifacts WHERE project_id = ? AND artifact_type = 'music_file' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return row["file_path"] if row else None
    def _build_narration_track(
        self,
        project_id: str,
        rendered_scenes: list[dict],
        output_dir: str,
        xfade_dur: float = 0.5,
    ) -> str | None:
        """Build a narration track aligned to the xfade video timeline.

        Each audio segment is placed at its scene's xfade-aware start offset
        on a silent canvas of total_video_duration length.  Audio is allowed
        to play its full natural duration so no words are clipped at scene
        boundaries.  During xfade overlap regions the outgoing and incoming
        narration will briefly overlap — this sounds natural and mirrors the
        visual crossfade.

        Uses an iterative overlay approach: start with silence, then mix in
        one audio segment at a time using ``adelay`` + ``amix``.  This avoids
        the fragile 33-input ``amix`` that can silently fail.
        """
        import os
        import subprocess

        rows = self._conn.execute(
            "SELECT scene_number, audio_file_path, status "
            "FROM audio_segments WHERE project_id = ? ORDER BY scene_number",
            (project_id,),
        ).fetchall()

        audio_map: dict[int, str | None] = {}
        for r in rows:
            path = r["audio_file_path"]
            if r["status"] in ("SYNTHESIZED", "UPLOADED") and path and os.path.isfile(path):
                audio_map[r["scene_number"]] = path
            else:
                audio_map.setdefault(r["scene_number"], None)

        if not audio_map:
            logger.info("No audio segments for project %s — skipping narration track", project_id)
            return None

        # ── Probe video clip durations ──
        video_durations: list[float] = []
        for scene in rendered_scenes:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", scene["rendered_path"]],
                capture_output=True, text=True,
            )
            dur = float(probe.stdout.strip()) if probe.stdout.strip() else 8.0
            video_durations.append(dur)

        # ── Compute xfade-aware start offsets (mirrors start_render) ──
        scene_offsets: list[float] = [0.0]
        cumulative = video_durations[0]
        for i in range(1, len(rendered_scenes)):
            transition = rendered_scenes[i].get("transition", "fade") or "fade"
            xfade_d = 0.01 if transition == "none" else xfade_dur
            offset = max(0.0, cumulative - xfade_d)
            scene_offsets.append(offset)
            cumulative = offset + video_durations[i]

        total_video_duration = cumulative
        logger.info(
            "Narration track: %d scenes, %.1fs total video, %.1fs xfade overlap",
            len(rendered_scenes), total_video_duration,
            sum(video_durations) - total_video_duration,
        )

        # ── Normalize all audio to WAV 44100/stereo first ──
        prep_dir = os.path.join(output_dir, "narration_trimmed")
        os.makedirs(prep_dir, exist_ok=True)

        # Breathing room: shift each scene's audio start by a small pad so
        # narration doesn't feel rushed at scene boundaries.  The first scene
        # starts at t=0 (no pad).  Configurable via NARRATION_PAD_MS env var.
        pad_ms = int(os.environ.get("NARRATION_PAD_MS", "300"))
        pad_s = pad_ms / 1000.0

        prepared: list[tuple[int, str, float]] = []  # (idx, wav_path, offset)
        for idx, scene in enumerate(rendered_scenes):
            scene_num = scene["scene_number"]
            audio_path = audio_map.get(scene_num)
            if not audio_path:
                continue

            wav_path = os.path.join(prep_dir, f"norm_{idx:03d}.wav")
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path,
                 "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                 wav_path],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                logger.warning("Failed to normalize scene %d audio: %s", scene_num, result.stderr[:200])
                continue

            offset = scene_offsets[idx] + (pad_s if idx > 0 else 0.0)
            prepared.append((idx, wav_path, offset))

        if not prepared:
            logger.info("No valid audio segments after normalization")
            return None

        # ── Create silent base track ──
        base_path = os.path.join(output_dir, "narration_base.wav")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"anullsrc=r=44100:cl=stereo",
             "-t", f"{total_video_duration:.3f}",
             "-c:a", "pcm_s16le", base_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logger.error("Failed to create silence base: %s", result.stderr[:300])
            return None

        # ── Iteratively overlay each audio segment onto the base ──
        # Process in batches of 8 to avoid too many iterations while
        # keeping each FFmpeg command simple and reliable.
        current_base = base_path
        batch_size = 8

        for batch_start in range(0, len(prepared), batch_size):
            batch = prepared[batch_start:batch_start + batch_size]
            batch_out = os.path.join(
                output_dir, f"narration_pass_{batch_start}.wav"
            )

            inputs = ["-i", current_base]
            filter_parts = []
            mix_labels = ["[0:a]"]

            for bi, (idx, wav_path, offset_s) in enumerate(batch):
                input_idx = bi + 1
                inputs += ["-i", wav_path]
                delay_ms = int(offset_s * 1000)
                label = f"[d{bi}]"
                filter_parts.append(
                    f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}:all=1{label}"
                )
                mix_labels.append(label)

            n_inputs = len(mix_labels)
            mix_str = "".join(mix_labels)
            filter_parts.append(
                f"{mix_str}amix=inputs={n_inputs}:duration=first"
                f":dropout_transition=0:normalize=0[aout]"
            )
            filter_str = ";".join(filter_parts)

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_str,
                "-map", "[aout]",
                "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
                batch_out,
            ]
            logger.info(
                "Narration overlay batch %d–%d (%d segments)",
                batch_start, batch_start + len(batch) - 1, len(batch),
            )
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(
                    "Narration overlay batch failed: %s", result.stderr[:500]
                )
                return None

            current_base = batch_out

        # ── Final trim to exact video duration ──
        narration_path = os.path.join(output_dir, "narration_full.wav")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", current_base,
             "-af", f"atrim=0:{total_video_duration:.3f}",
             "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
             narration_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logger.error("Final narration trim failed: %s", result.stderr[:300])
            return None

        # Verify duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", narration_path],
            capture_output=True, text=True,
        )
        if probe.stdout.strip():
            nar_dur = float(probe.stdout.strip())
            logger.info(
                "Narration track: %.2fs (video: %.2fs, diff: %.2fs)",
                nar_dur, total_video_duration, nar_dur - total_video_duration,
            )

        return narration_path


    def _get_music_settings(self, project_id: str) -> dict:
        """Get music settings for a project."""
        row = self._conn.execute(
            "SELECT metadata_json FROM artifacts WHERE project_id = ? AND artifact_type = 'music_settings' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if row and row["metadata_json"]:
            import json as _json
            try:
                return _json.loads(row["metadata_json"]) if isinstance(row["metadata_json"], str) else row["metadata_json"]
            except Exception:
                pass
        return {"volume": 80, "fade_in_ms": 1000, "fade_out_ms": 2000}

    def get_render_status(self, project_id: str) -> dict | None:
        """Get the latest render job status (prefers jobs with actual output)."""
        jobs = self._job_runner.list_jobs(project_id)
        render_jobs = [j for j in jobs if j.job_type == "render_final"]
        if not render_jobs:
            return None
        # Prefer the latest job that has an actual output_path
        for j in render_jobs:
            output = j.output_json if isinstance(j.output_json, dict) else {}
            if output.get("output_path"):
                return {
                    "job_id": j.id, "status": j.status.value,
                    "output": j.output_json, "error": j.error,
                }
        # Fall back to the most recent render job
        j = render_jobs[0]
        return {
            "job_id": j.id, "status": j.status.value,
            "output": j.output_json, "error": j.error,
        }

    def list_render_history(self, project_id: str) -> list[dict]:
        """Get all render jobs for a project, newest first."""
        jobs = self._job_runner.list_jobs(project_id)
        render_jobs = [j for j in jobs if j.job_type == "render_final"]
        results = []
        for i, j in enumerate(render_jobs):
            output = j.output_json if isinstance(j.output_json, dict) else {}
            has_file = bool(output.get("output_path"))
            results.append({
                "job_id": j.id,
                "status": j.status.value,
                "output": j.output_json,
                "error": j.error,
                "created_at": j.created_at,
                "is_latest": i == 0 and has_file,
                "has_file": has_file,
            })
        return results
