"""Research router — per-source trigger endpoints."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from studio_api.dependencies import get_db
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.research_service import ResearchService

router = APIRouter(prefix="/api/projects/{project_id}/research", tags=["research"])


class YouTubeSearchRequest(BaseModel):
    keywords: list[str] | None = None


def _get_research_service(conn: sqlite3.Connection = Depends(get_db)) -> ResearchService:
    return ResearchService(conn, JobRunner(conn))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.post("/youtube", status_code=202)
def search_youtube(
    project_id: str = Depends(_verify_project),
    body: YouTubeSearchRequest | None = None,
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        keywords = body.keywords if body else None
        return service.search_youtube(project_id, keywords=keywords)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.post("/reddit", status_code=202)
def search_reddit(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        return service.search_reddit(project_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.post("/trends", status_code=202)
def search_trends(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        return service.search_trends(project_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.post("/finance", status_code=202)
def search_finance(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        return service.search_finance(project_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.post("/wikipedia", status_code=202)
def search_wikipedia(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        return service.search_wikipedia(project_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.post("/cross-reference", status_code=202)
def cross_reference(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> dict:
    try:
        return service.cross_reference(project_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })


@router.get("/results")
def get_results(
    project_id: str = Depends(_verify_project),
    service: ResearchService = Depends(_get_research_service),
) -> list[dict]:
    return service.get_results(project_id)
