"""Scripts router — CRUD, finalize, diff, and AI generation endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from studio_api.dependencies import get_db
from studio_api.models.script import (
    DiffResult,
    ScriptVersionCreate,
    ScriptVersionResponse,
    ScriptVersionUpdate,
)
from studio_api.services.project_service import ProjectService
from studio_api.services.script_service import ScriptService

router = APIRouter(prefix="/api/projects/{project_id}/scripts", tags=["scripts"])


class GenerateRequest(BaseModel):
    topic_id: str
    title: str
    raw_text: str


class ImportScriptRequest(BaseModel):
    script_json: dict
    title: str | None = None


def _get_script_service(conn: sqlite3.Connection = Depends(get_db)) -> ScriptService:
    return ScriptService(conn)


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.get("", response_model=list[ScriptVersionResponse])
def list_scripts(
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> list[ScriptVersionResponse]:
    return service.list_for_project(project_id)


@router.post("", response_model=ScriptVersionResponse, status_code=201)
def create_script(
    data: ScriptVersionCreate,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    return service.create(project_id, data)


@router.post("/generate", response_model=ScriptVersionResponse, status_code=201)
def generate_script(
    body: GenerateRequest,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    """Use AI (ScriptConverter) to split raw text into scenes and create a script version."""
    try:
        return service.generate_from_raw(project_id, body.topic_id, body.title, body.raw_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail={
            "type": "generation_error", "message": str(e)
        })
@router.post("/import", response_model=ScriptVersionResponse, status_code=201)
def import_script(
    body: ImportScriptRequest,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    """Import a pre-built script JSON directly (no LLM). Auto-finalized."""
    try:
        return service.import_json(project_id, body.script_json, body.title)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error", "message": str(e)
        })


@router.delete("", status_code=204)
def delete_all_scripts(
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> None:
    service.delete_all(project_id)


@router.get("/diff", response_model=DiffResult)
def diff_scripts(
    project_id: str = Depends(_verify_project),
    v1: int = Query(...),
    v2: int = Query(...),
    service: ScriptService = Depends(_get_script_service),
) -> DiffResult:
    result = service.diff(v1, v2)
    if result is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": "One or both script versions not found"
        })
    return result


@router.get("/{version_id}", response_model=ScriptVersionResponse)
def get_script(
    version_id: int,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    script = service.get(version_id)
    if script is None or script.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Script version {version_id} not found"
        })
    return script


@router.patch("/{version_id}", response_model=ScriptVersionResponse)
def update_script(
    version_id: int,
    data: ScriptVersionUpdate,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    existing = service.get(version_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Script version {version_id} not found"
        })
    try:
        return service.update(version_id, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={
            "type": "conflict", "message": str(e)
        })


@router.post("/{version_id}/finalize", response_model=ScriptVersionResponse)
def finalize_script(
    version_id: int,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    existing = service.get(version_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Script version {version_id} not found"
        })
    return service.finalize(version_id)


@router.post("/{version_id}/enrich-keywords", response_model=ScriptVersionResponse)
def enrich_keywords(
    version_id: int,
    project_id: str = Depends(_verify_project),
    service: ScriptService = Depends(_get_script_service),
) -> ScriptVersionResponse:
    """Run keyword research on all stock scenes in a script version.

    This is opt-in — the user triggers it when they want AI-researched
    keywords instead of their manually provided ones.
    """
    existing = service.get(version_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Script version {version_id} not found"
        })
    try:
        result = service.enrich_keywords(version_id)
        if result is None:
            raise HTTPException(status_code=404, detail={
                "type": "not_found", "message": f"Script version {version_id} not found"
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail={
            "type": "enrichment_error", "message": str(e)
        })
