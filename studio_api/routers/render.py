"""Render router — start render, status, reorder."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from studio_api.dependencies import get_db
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.render_service import RenderService

router = APIRouter(prefix="/api/projects/{project_id}/render", tags=["render"])


class ReorderRequest(BaseModel):
    scene_ids: list[int]


def _get_render_service(conn: sqlite3.Connection = Depends(get_db)) -> RenderService:
    return RenderService(conn, job_runner=JobRunner(conn))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.post("", status_code=202)
def start_render(
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
) -> dict:
    try:
        return service.start_render(project_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error", "message": str(e)
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.get("/status")
def render_status(
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
) -> dict:
    status = service.get_render_status(project_id)
    if status is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": "No render job found"
        })
    return status


@router.get("/history")
def render_history(
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
) -> list[dict]:
    return service.list_render_history(project_id)


@router.post("/reorder")
def reorder_scenes(
    body: ReorderRequest,
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
) -> list[dict]:
    return service.reorder_scenes(project_id, body.scene_ids)


@router.get("/output")
def get_render_output(
    project_id: str = Depends(_verify_project),
    service: RenderService = Depends(_get_render_service),
    job_id: str | None = None,
):
    """Serve a rendered video file. If job_id is given, serve that version."""
    import os
    if job_id:
        # Serve specific version
        job = service._job_runner.get_job(job_id)
        if job and job.output_json and isinstance(job.output_json, dict):
            path = job.output_json.get("output_path")
            if path and os.path.isfile(path):
                return FileResponse(path, media_type="video/mp4", filename=f"render_{job_id[:8]}.mp4")
        raise HTTPException(status_code=404, detail={"type": "not_found", "message": "Render output not found for this job"})
    # Default: latest
    path = service.get_final_output_path(project_id)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": "No final render output available"
        })
    return FileResponse(path, media_type="video/mp4", filename=f"final_{project_id[:8]}.mp4")
