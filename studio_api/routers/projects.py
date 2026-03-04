"""Projects router — CRUD endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from studio_api.models.project import ProjectCreate, ProjectResponse, ProjectUpdate
from studio_api.services.project_service import ProjectService
from studio_api.dependencies import get_db

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_service(conn: sqlite3.Connection = Depends(get_db)) -> ProjectService:
    return ProjectService(conn)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(_get_service),
) -> ProjectResponse:
    return service.create(data)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    service: ProjectService = Depends(_get_service),
) -> list[ProjectResponse]:
    return service.list_all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    service: ProjectService = Depends(_get_service),
) -> ProjectResponse:
    project = service.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found",
            "message": f"Project {project_id} not found",
        })
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    service: ProjectService = Depends(_get_service),
) -> ProjectResponse:
    project = service.update(project_id, data)
    if project is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found",
            "message": f"Project {project_id} not found",
        })
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    service: ProjectService = Depends(_get_service),
) -> None:
    if not service.delete(project_id):
        raise HTTPException(status_code=404, detail={
            "type": "not_found",
            "message": f"Project {project_id} not found",
        })
