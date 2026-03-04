"""Audio router — timeline generation, segment CRUD, synthesis."""

from __future__ import annotations

import logging
import os
import queue
import sqlite3
import threading

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field

from studio_api.dependencies import get_db
from studio_api.models.audio import AudioSegmentResponse, AudioSegmentUpdate, AudioTimelineResponse
from studio_api.services.audio_service import AudioService
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/audio", tags=["audio"])

_logger = logging.getLogger(__name__)

# Global synthesis queue — processes TTS jobs with configurable concurrency.
# Fish Speech local CAN handle concurrent requests (server queues internally).
# Cloud backends (Fish Audio, ElevenLabs) support full parallelism.
_synth_queue: queue.Queue[tuple[str, int]] = queue.Queue()
_synth_workers_started = False
_synth_lock = threading.Lock()
_SYNTH_CONCURRENCY = int(os.getenv("SYNTH_CONCURRENCY", "4"))


def _start_synth_worker():
    """Start the synthesis worker threads if not already running."""
    global _synth_workers_started
    with _synth_lock:
        if _synth_workers_started:
            return
        _synth_workers_started = True

    def _worker(worker_id: int):
        while True:
            project_id, segment_id = _synth_queue.get()
            try:
                import sqlite3 as _sqlite3
                from studio_api.dependencies import get_db_path
                conn = _sqlite3.connect(get_db_path(), timeout=30)
                conn.row_factory = _sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                try:
                    # Mark RUNNING now that this segment is actually being processed
                    conn.execute("UPDATE audio_segments SET status = 'RUNNING' WHERE id = ?", (segment_id,))
                    conn.commit()
                    _logger.info("Worker %d: synthesizing segment %d", worker_id, segment_id)
                    svc = AudioService(conn, job_runner=JobRunner(conn))
                    svc.synthesize_segment(project_id, segment_id)
                except Exception as e:
                    _logger.error("Worker %d: synthesis failed for segment %s: %s", worker_id, segment_id, e)
                    try:
                        conn.execute("UPDATE audio_segments SET status = 'FAILED' WHERE id = ?", (segment_id,))
                        conn.commit()
                    except Exception:
                        pass
                finally:
                    conn.close()
            except Exception as e:
                _logger.error("Synth worker %d error: %s", worker_id, e)
            finally:
                _synth_queue.task_done()

    # Start multiple worker threads
    for i in range(_SYNTH_CONCURRENCY):
        t = threading.Thread(target=_worker, args=(i,), daemon=True)
        t.start()
        _logger.info("Started synthesis worker %d", i)
    _logger.info("Synthesis pool: %d concurrent workers", _SYNTH_CONCURRENCY)


class TimelineRequest(BaseModel):
    script_version_id: int


class PauseRequest(BaseModel):
    duration_ms: int = Field(default=500, ge=100, le=5000)


def _get_audio_service(conn: sqlite3.Connection = Depends(get_db)) -> AudioService:
    return AudioService(conn, job_runner=JobRunner(conn))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.post("/timeline", response_model=AudioTimelineResponse, status_code=201)
def generate_timeline(
    body: TimelineRequest,
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> AudioTimelineResponse:
    try:
        return service.generate_timeline(project_id, body.script_version_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error", "message": str(e)
        })


@router.get("/segments", response_model=list[AudioSegmentResponse])
def list_segments(
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> list[AudioSegmentResponse]:
    return service.list_segments(project_id)


@router.delete("/segments", status_code=204)
def delete_all_segments(
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> None:
    service.delete_all_segments(project_id)


@router.patch("/segments/{segment_id}", response_model=AudioSegmentResponse)
def update_segment(
    segment_id: int,
    data: AudioSegmentUpdate,
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> AudioSegmentResponse:
    result = service.update_segment(segment_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Segment {segment_id} not found"
        })
    return result


@router.post("/segments/{segment_id}/synthesize", status_code=202)
def synthesize_segment(
    segment_id: int,
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> dict:
    seg = service.get_segment(segment_id)
    if seg is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Segment {segment_id} not found"
        })

    # Mark as QUEUED and submit to the serialized synthesis queue
    service._conn.execute("UPDATE audio_segments SET status = 'QUEUED' WHERE id = ?", (segment_id,))
    service._conn.commit()

    _start_synth_worker()
    _synth_queue.put((project_id, segment_id))

    return {"status": "queued", "segment_id": segment_id}


@router.post("/segments/{segment_id}/pause", response_model=AudioSegmentResponse, status_code=201)
def insert_pause(
    segment_id: int,
    body: PauseRequest | None = None,
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> AudioSegmentResponse:
    try:
        duration_ms = body.duration_ms if body else 500
        return service.insert_pause(project_id, segment_id, duration_ms)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": str(e)
        })


@router.get("/segments/{segment_id}/preview")
def preview_segment(
    segment_id: int,
    project_id: str,
):
    """Serve audio file for playback.

    Uses its own DB connection to avoid threading issues when multiple
    audio players load concurrently."""
    import sqlite3 as _sqlite3
    from studio_api.dependencies import get_db_path
    conn = _sqlite3.connect(get_db_path(), timeout=30)
    conn.row_factory = _sqlite3.Row
    try:
        # Verify project exists
        proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if proj is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": f"Project {project_id} not found"})
        # Get segment
        row = conn.execute("SELECT * FROM audio_segments WHERE id = ?", (segment_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": f"Segment {segment_id} not found"})
        audio_path = row["audio_file_path"]
        if not audio_path or not os.path.isfile(audio_path):
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": "Audio file not available"})
        media_type = "audio/mpeg" if audio_path.endswith(".mp3") else "audio/wav"
        with open(audio_path, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Cache-Control": "no-store, must-revalidate",
                "Content-Length": str(len(content)),
            },
        )
    finally:
        conn.close()

@router.post("/upload", status_code=202)
def upload_master_audio(
    project_id: str,
    file: UploadFile = File(...),
    whisper_model: str = Form("base"),
):
    """Upload a master audio recording. Backend transcribes, aligns to script
    scenes, and splits into per-segment audio files."""
    import sqlite3 as _sqlite3
    from studio_api.dependencies import get_db_path

    if not file.filename:
        raise HTTPException(status_code=400, detail={"type": "validation_error", "message": "No file provided"})

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("wav", "mp3", "m4a", "flac", "ogg", "webm"):
        raise HTTPException(status_code=400, detail={
            "type": "validation_error",
            "message": f"Unsupported format: .{ext}. Use WAV, MP3, M4A, FLAC, OGG, or WebM."
        })

    # Save uploaded file
    upload_dir = f"output/audio/{project_id}"
    os.makedirs(upload_dir, exist_ok=True)
    master_path = os.path.join(upload_dir, f"master.{ext}")
    with open(master_path, "wb") as f:
        content = file.file.read()
        f.write(content)

    _logger.info("Saved master audio: %s (%d bytes)", master_path, len(content))

    # Run transcription + alignment + splitting in a background thread
    # to avoid blocking the request (Whisper can take a while)
    def _process():
        conn = _sqlite3.connect(get_db_path(), timeout=30)
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            svc = AudioService(conn, job_runner=JobRunner(conn))
            svc.upload_master_audio(project_id, master_path, whisper_model=whisper_model)
        except Exception as e:
            _logger.error("Master audio processing failed: %s", e, exc_info=True)
        finally:
            conn.close()

    t = threading.Thread(target=_process, daemon=True)
    t.start()

    return {"status": "processing", "message": "Master audio uploaded. Transcribing and splitting..."}




@router.delete("/segments/{segment_id}", status_code=204)
def delete_segment(
    segment_id: int,
    project_id: str = Depends(_verify_project),
    service: AudioService = Depends(_get_audio_service),
) -> None:
    deleted = service.delete_segment(segment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Segment {segment_id} not found"
        })

@router.post("/finalize", status_code=200)
def finalize_audio(
    project_id: str = Depends(_verify_project),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Finalize audio — advance project stage to VISUAL and auto-create scenes."""
    svc = AudioService(conn, job_runner=JobRunner(conn))
    segments = svc.list_segments(project_id)

    if not segments:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error",
            "message": "No audio segments to finalize",
        })

    not_ready = [s for s in segments if s.status not in ("SYNTHESIZED", "UPLOADED")]
    if not_ready:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error",
            "message": f"{len(not_ready)} segment(s) not yet synthesized",
        })

    # Advance project stage to VISUAL
    from studio_api.models.project import PipelineStage
    from studio_api.services.project_service import ProjectService
    from studio_api.models.project import ProjectUpdate
    proj_svc = ProjectService(conn)
    proj_svc.update(project_id, ProjectUpdate(current_stage=PipelineStage.VISUAL))

    # Auto-create visual scenes if none exist yet
    from studio_api.services.visual_service import VisualService
    vis_svc = VisualService(conn, job_runner=JobRunner(conn))
    existing_scenes = vis_svc.list_scenes(project_id)
    scenes_created = 0
    if not existing_scenes:
        # Find the script version used for the audio timeline
        sv_id = segments[0].script_version_id
        if sv_id:
            try:
                vis_svc.create_scenes_from_script(project_id, sv_id)
                scenes_created = len(vis_svc.list_scenes(project_id))
            except Exception as e:
                _logger.warning("Auto-create scenes failed: %s", e)

    return {
        "status": "finalized",
        "segment_count": len(segments),
        "scenes_created": scenes_created,
    }


