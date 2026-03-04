"""Audio service — SRT timeline generation, segment management, synthesis."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from studio_api.models.audio import (
    AudioSegmentResponse,
    AudioSegmentUpdate,
    AudioTimelineResponse,
)
from studio_api.services.job_runner import JobRunner

logger = logging.getLogger(__name__)

# Baseline words-per-minute for duration estimation
_WPM = 150


def _estimate_duration_seconds(text: str) -> float:
    """Estimate speech duration from word count at 150 WPM."""
    words = len(text.split())
    return max(1.0, (words / _WPM) * 60)


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_time(srt: str) -> float:
    """Parse SRT format HH:MM:SS,mmm to seconds."""
    parts = srt.replace(",", ".").split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


class AudioService:
    """Manages audio segments and SRT timeline generation."""

    def __init__(self, conn: sqlite3.Connection, job_runner: JobRunner | None = None) -> None:
        self._conn = conn
        self._job_runner = job_runner

    def generate_timeline(self, project_id: str, script_version_id: int) -> AudioTimelineResponse:
        """Generate SRT timeline segments from a finalized script version."""
        row = self._conn.execute(
            "SELECT * FROM script_versions WHERE id = ? AND project_id = ?",
            (script_version_id, project_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"Script version {script_version_id} not found")
        if not row["is_finalized"]:
            raise ValueError("Script must be finalized before generating timeline")

        script_json = json.loads(row["script_json"]) if isinstance(row["script_json"], str) else row["script_json"]
        scenes = script_json.get("scenes", [])

        # Read configured TTS speed from env for default voice_params
        import os
        default_speed = float(os.getenv("FISH_SPEED", "0.9"))
        default_voice_params = json.dumps({
            "speed": default_speed,
            "temperature": 0.6,
            "top_p": 0.7,
            "repetition_penalty": 1.4,
            "emotion": "neutral",
            "pitch": 0.0,
            "emphasis": "none",
        })

        now = datetime.now(timezone.utc).isoformat()
        current_time = 0.0
        segments = []

        for scene in scenes:
            narration = scene.get("narration_text") or scene.get("narration", "")
            if not narration.strip():
                continue
            scene_num = scene.get("scene_number", 0)
            scene_emotion = scene.get("emotion", "neutral") or "neutral"
            duration = _estimate_duration_seconds(narration)
            start = _format_srt_time(current_time)
            end = _format_srt_time(current_time + duration)

            # Per-scene voice params with emotion from script
            scene_voice_params = json.dumps({
                "speed": default_speed,
                "temperature": 0.6,
                "top_p": 0.7,
                "repetition_penalty": 1.4,
                "emotion": scene_emotion,
                "pitch": 0.0,
                "emphasis": "none",
            })

            cursor = self._conn.execute(
                "INSERT INTO audio_segments (project_id, script_version_id, scene_number, "
                "start_time, end_time, narration_text, voice_params_json, status, version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 1, ?)",
                (project_id, script_version_id, scene_num, start, end, narration, scene_voice_params, now),
            )
            segments.append(self._get_segment(cursor.lastrowid))
            current_time += duration

        self._conn.commit()
        total_duration = _format_srt_time(current_time)
        return AudioTimelineResponse(
            segments=segments, total_duration=total_duration, segment_count=len(segments)
        )

    def list_segments(self, project_id: str) -> list[AudioSegmentResponse]:
        rows = self._conn.execute(
            "SELECT * FROM audio_segments WHERE project_id = ? ORDER BY scene_number",
            (project_id,),
        ).fetchall()
        return [self._row_to_response(r) for r in rows]

    def get_segment(self, segment_id: int) -> AudioSegmentResponse | None:
        return self._get_segment(segment_id)

    def update_segment(self, segment_id: int, data: AudioSegmentUpdate) -> AudioSegmentResponse | None:
        existing = self._get_segment(segment_id)
        if existing is None:
            return None

        fields = []
        values = []
        if data.narration_text is not None:
            fields.append("narration_text = ?")
            values.append(data.narration_text)
        if data.start_time is not None:
            fields.append("start_time = ?")
            values.append(data.start_time)
        if data.end_time is not None:
            fields.append("end_time = ?")
            values.append(data.end_time)
        if data.voice_params is not None:
            fields.append("voice_params_json = ?")
            values.append(json.dumps(data.voice_params.model_dump()))

        if not fields:
            return existing

        values.append(segment_id)
        self._conn.execute(
            f"UPDATE audio_segments SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return self._get_segment(segment_id)

    def insert_pause(self, project_id: str, after_segment_id: int, duration_ms: int = 500) -> AudioSegmentResponse:
        """Insert a silence segment after the given segment."""
        ref = self._get_segment(after_segment_id)
        if ref is None:
            raise ValueError(f"Segment {after_segment_id} not found")

        pause_seconds = duration_ms / 1000.0
        start_seconds = _parse_srt_time(ref.end_time)
        start = _format_srt_time(start_seconds)
        end = _format_srt_time(start_seconds + pause_seconds)
        now = datetime.now(timezone.utc).isoformat()

        cursor = self._conn.execute(
            "INSERT INTO audio_segments (project_id, script_version_id, scene_number, "
            "start_time, end_time, narration_text, status, version, created_at) "
            "VALUES (?, ?, ?, ?, ?, '[pause]', 'SYNTHESIZED', 1, ?)",
            (project_id, ref.script_version_id, ref.scene_number, start, end, now),
        )
        self._conn.commit()
        return self._get_segment(cursor.lastrowid)

    def delete_segment(self, segment_id: int) -> bool:
        """Delete an audio segment by ID. Returns True if deleted."""
        existing = self._get_segment(segment_id)
        if existing is None:
            return False
        self._conn.execute("DELETE FROM audio_segments WHERE id = ?", (segment_id,))
        self._conn.commit()
        return True
    def delete_all_segments(self, project_id: str) -> int:
        """Delete all audio segments for a project. Returns count deleted."""
        cursor = self._conn.execute(
            "DELETE FROM audio_segments WHERE project_id = ?", (project_id,)
        )
        self._conn.commit()
        return cursor.rowcount

    def synthesize_segment(self, project_id: str, segment_id: int) -> dict:
        """Synthesize audio for a single segment."""
        if self._job_runner is None:
            raise RuntimeError("JobRunner not configured")

        seg = self._get_segment(segment_id)
        if seg is None:
            raise ValueError(f"Segment {segment_id} not found")

        job = self._job_runner.create_job(project_id, "synthesize_audio", input_data={"segment_id": segment_id})
        self._job_runner.start_job(job.id)
        try:
            from voice_synthesizer.synthesizer import VoiceSynthesizer
            from voice_synthesizer.config import VoiceConfig

            # Use project-specific output dir with segment_id in filename to avoid collisions
            output_dir = f"output/audio/{project_id}"
            # Apply per-segment voice params
            vp = seg.voice_params
            config_kwargs: dict[str, Any] = {"output_dir": output_dir}
            if vp:
                config_kwargs["fish_speed"] = vp.speed
                config_kwargs["fish_temperature"] = vp.temperature
                config_kwargs["fish_top_p"] = vp.top_p
            config = VoiceConfig(**config_kwargs)

            # Override repetition_penalty on the client after init
            synth = VoiceSynthesizer(config)
            if vp and hasattr(synth, 'client') and hasattr(synth.client, 'repetition_penalty'):
                synth.client.repetition_penalty = vp.repetition_penalty

            class _MiniScene:
                def __init__(self, sn, text, emotion="neutral"):
                    self.scene_number = sn
                    self.narration_text = text
                    self.emotion = emotion

            class _MiniScript:
                def __init__(self, scenes):
                    self.scenes = scenes

            # Emotion: prefer per-segment override, fall back to script's scene emotion
            emotion = (vp.emotion if vp and vp.emotion != "neutral" else None) or "neutral"
            if emotion == "neutral" and seg.script_version_id:
                sv_row = self._conn.execute(
                    "SELECT script_json FROM script_versions WHERE id = ?",
                    (seg.script_version_id,),
                ).fetchone()
                if sv_row:
                    sj = json.loads(sv_row["script_json"]) if isinstance(sv_row["script_json"], str) else sv_row["script_json"]
                    for sc in sj.get("scenes", []):
                        if sc.get("scene_number") == seg.scene_number:
                            emotion = sc.get("emotion", "neutral")
                            break

            # Use segment_id as scene_number for unique filenames
            mini = _MiniScript([_MiniScene(segment_id, seg.narration_text, emotion)])
            manifest = synth.synthesize(mini)

            if manifest.entries and manifest.entries[0].file_path:
                file_path = manifest.entries[0].file_path
                self._conn.execute(
                    "UPDATE audio_segments SET audio_file_path = ?, status = 'SYNTHESIZED' WHERE id = ?",
                    (file_path, segment_id),
                )
                self._conn.commit()
                self._job_runner.complete_job(job.id, output_data={"file_path": file_path})
                return {"job_id": job.id, "file_path": file_path}
            else:
                error = manifest.entries[0].error if manifest.entries else "No output"
                raise RuntimeError(error)
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def upload_master_audio(
        self,
        project_id: str,
        audio_path: str,
        whisper_model: str = "base",
    ) -> dict:
        """Upload a master audio recording, transcribe it, align to script scenes, and split.

        Steps:
        1. Whisper STT → word-level timestamps
        2. Align transcript to existing audio segments (by narration text)
        3. Split master audio at scene boundaries via ffmpeg
        4. Update each segment's audio_file_path and status → UPLOADED
        """
        from voice_synthesizer.audio_splitter import (
            transcribe_with_timestamps,
            align_to_scenes,
            split_audio,
        )

        segments = self.list_segments(project_id)
        if not segments:
            raise ValueError("No audio segments found. Generate a timeline first.")

        # 1. Transcribe
        words = transcribe_with_timestamps(audio_path, model_size=whisper_model)
        if not words:
            raise ValueError("Whisper returned no words — is the audio file valid?")

        # 2. Build scene narrations in order
        scene_narrations = [
            (seg.scene_number, seg.narration_text)
            for seg in sorted(segments, key=lambda s: s.scene_number)
            if seg.narration_text and seg.narration_text.strip() and seg.narration_text != "[pause]"
        ]

        # 3. Align
        boundaries = align_to_scenes(words, scene_narrations)
        if not boundaries:
            raise ValueError("Could not align transcript to any scenes.")

        # 4. Split
        output_dir = f"output/audio/{project_id}"
        boundaries = split_audio(audio_path, boundaries, output_dir)

        # 5. Update segments in DB
        updated = 0
        # Build a map: scene_number → boundary
        boundary_map = {b.scene_number: b for b in boundaries if b.audio_path}
        for seg in segments:
            b = boundary_map.get(seg.scene_number)
            if b and b.audio_path:
                # Calculate actual duration from the split file
                duration = b.end_time - b.start_time
                start_srt = _format_srt_time(b.start_time)
                end_srt = _format_srt_time(b.end_time)
                self._conn.execute(
                    "UPDATE audio_segments SET audio_file_path = ?, status = 'UPLOADED', "
                    "start_time = ?, end_time = ? WHERE id = ?",
                    (b.audio_path, start_srt, end_srt, seg.id),
                )
                updated += 1

        self._conn.commit()
        logger.info("Upload complete: %d/%d segments updated", updated, len(segments))
        return {
            "updated_segments": updated,
            "total_segments": len(segments),
            "boundaries": [
                {"scene": b.scene_number, "start": b.start_time, "end": b.end_time, "path": b.audio_path}
                for b in boundaries
            ],
        }


    def _get_segment(self, segment_id: int) -> AudioSegmentResponse | None:
        row = self._conn.execute(
            "SELECT * FROM audio_segments WHERE id = ?", (segment_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> AudioSegmentResponse:
        from studio_api.models.audio import VoiceParams
        voice_params = row["voice_params_json"]
        if voice_params and isinstance(voice_params, str):
            try:
                voice_params = VoiceParams(**json.loads(voice_params))
            except (json.JSONDecodeError, Exception):
                voice_params = None
        return AudioSegmentResponse(
            id=row["id"],
            project_id=row["project_id"],
            script_version_id=row["script_version_id"],
            scene_number=row["scene_number"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            narration_text=row["narration_text"],
            voice_params=voice_params,
            audio_file_path=row["audio_file_path"],
            status=row["status"],
            version=row["version"],
            created_at=row["created_at"],
        )
