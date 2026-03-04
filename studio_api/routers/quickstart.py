"""Quickstart router — global endpoints for dashboard shortcuts."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from studio_api.dependencies import get_db
from studio_api.models.project import ProjectCreate
from studio_api.models.topic import TopicCreate, TopicResponse
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.research_service import ResearchService
from studio_api.services.topic_service import TopicService

router = APIRouter(prefix="/api", tags=["quickstart"])


class QuickStartRequest(BaseModel):
    title: str
    topic: str | None = None
    description: str = ""


@router.get("/topics/recent", response_model=list[TopicResponse])
def recent_topics(
    limit: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[TopicResponse]:
    """List recent topics across all projects."""
    rows = conn.execute(
        "SELECT * FROM topics ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    svc = TopicService(conn)
    return [svc._row_to_response(r) for r in rows]


@router.post("/quick-start", status_code=201)
def quick_start(
    body: QuickStartRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create a project and optionally a manual topic in one shot."""
    project_svc = ProjectService(conn)
    project = project_svc.create(ProjectCreate(title=body.title, description=body.description))

    topic = None
    if body.topic:
        topic_svc = TopicService(conn, job_runner=JobRunner(conn))
        topic = topic_svc.create(project.id, TopicCreate(title=body.topic, source="manual"))

    return {
        "project": project.model_dump() if hasattr(project, 'model_dump') else project.__dict__,
        "topic": topic.model_dump() if topic and hasattr(topic, 'model_dump') else (topic.__dict__ if topic else None),
    }


@router.post("/research/all-sources", status_code=202)
def research_all_sources(
    project_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Trigger all research sources for a project. Creates a project if none given."""
    project_svc = ProjectService(conn)

    if project_id:
        project = project_svc.get(project_id)
        if project is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": "Project not found"})
    else:
        project = project_svc.create(ProjectCreate(title="Research Session", description="Auto-created from trend search"))

    research_svc = ResearchService(conn, JobRunner(conn))
    jobs = []
    for source_fn, name in [
        (research_svc.search_trends, "trends"),
        (research_svc.search_reddit, "reddit"),
        (research_svc.search_youtube, "youtube"),
        (research_svc.search_finance, "finance"),
        (research_svc.search_wikipedia, "wikipedia"),
    ]:
        try:
            if name == "youtube":
                result = source_fn(project.id, keywords=None)
            else:
                result = source_fn(project.id)
            jobs.append({"source": name, "status": "triggered", **result})
        except Exception as e:
            jobs.append({"source": name, "status": "failed", "error": str(e)})

    return {"project_id": project.id, "jobs": jobs}
