"""Music router — upload, settings, preview."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from studio_api.dependencies import get_db
from studio_api.models.scene import MusicSettings
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.render_service import RenderService

router = APIRouter(prefix="/api/projects/{project_id}/music", tags=["music"])


def _get_render_service(conn: sqlite3.Connection = Depends(get_db)) -> RenderService:
    return RenderService(conn, job_runner=JobRunner(conn))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.post("/upload", status_code=201)
async def upload_music(
    project_id: str = Depends(_verify_project),
    file: UploadFile = File(...),
    service: RenderService = Depends(_get_render_service),
) -> dict:
    if not file.filename or not file.filename.lower().endswith((".mp3", ".wav")):
        raise HTTPException(status_code=422, detail={
            "type": "validation_error", "message": "Only MP3 and WAV files are accepted"
        })
    data = await file.read()
    return service.upload_music(project_id, file.filename, data)


@router.patch("/settings")
def update_settings(
    settings: MusicSettings,
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
) -> dict:
    return service.update_music_settings(project_id, settings)
