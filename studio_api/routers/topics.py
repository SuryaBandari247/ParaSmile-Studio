"""Topics router — CRUD + pitch generation endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from studio_api.dependencies import get_db
from studio_api.models.topic import TopicCreate, TopicResponse, TopicUpdate
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.topic_service import TopicService

router = APIRouter(prefix="/api/projects/{project_id}/topics", tags=["topics"])


def _get_topic_service(conn: sqlite3.Connection = Depends(get_db)) -> TopicService:
    return TopicService(conn, job_runner=JobRunner(conn))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.get("", response_model=list[TopicResponse])
def list_topics(
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> list[TopicResponse]:
    return service.list_for_project(project_id)


@router.post("", response_model=TopicResponse, status_code=201)
def create_topic(
    data: TopicCreate,
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> TopicResponse:
    return service.create(project_id, data)


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: str,
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> TopicResponse:
    topic = service.get(topic_id)
    if topic is None or topic.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Topic {topic_id} not found"
        })
    return topic


@router.patch("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: str,
    data: TopicUpdate,
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> TopicResponse:
    existing = service.get(topic_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Topic {topic_id} not found"
        })
    updated = service.update(topic_id, data)
    return updated


@router.delete("/{topic_id}", status_code=204)
def delete_topic(
    topic_id: str,
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> None:
    existing = service.get(topic_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Topic {topic_id} not found"
        })
    service.delete(topic_id)


@router.post("/{topic_id}/pitch", status_code=202)
def generate_pitch(
    topic_id: str,
    project_id: str = Depends(_verify_project),
    service: TopicService = Depends(_get_topic_service),
) -> dict:
    existing = service.get(topic_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Topic {topic_id} not found"
        })
    try:
        return service.generate_pitch(project_id, topic_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "type": "external_error", "message": str(e)
        })
