"""Visuals router — scene CRUD, footage search, render."""

from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from studio_api.dependencies import get_db
from studio_api.models.scene import FootageResult, PixabayVideoResult, SceneCreate, SceneResponse, SceneUpdate, UnsplashPhotoResult, WikimediaImageResult
from studio_api.routers.websocket import manager as ws_manager
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.services.visual_service import VisualService

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["visuals"])


class CreateScenesRequest(BaseModel):
    script_version_id: int


class SearchFootageRequest(BaseModel):
    query: str
    source: str = "pexels"  # "pexels", "pixabay", "wikimedia", "unsplash", or "all"


class SelectFootageRequest(BaseModel):
    stock_video_path: str
    source: str = "pexels"  # "pexels", "pixabay", or "wikimedia"
    attribution: str | None = None
    stock_title: str | None = None


class NarrativeBeatResponse(BaseModel):
    beat: str
    timestamp_hint: str | None = None
    suggested_keywords: list[str] = []


class KeywordSuggestionResponse(BaseModel):
    keyword: str
    rank: int
    original_term: str | None = None
    visual_synonym: str | None = None
    category: str | None = None
    source_hints: dict[str, str] | None = None


class SuggestKeywordsResponse(BaseModel):
    suggestions: list[KeywordSuggestionResponse]
    aesthetic_hints: list[str]
    keyword_categories: dict[str, list[str]] = {}
    narrative_beats: list[NarrativeBeatResponse] = []


def _get_visual_service(conn: sqlite3.Connection = Depends(get_db)) -> VisualService:
    return VisualService(conn, job_runner=JobRunner(conn, broadcast=ws_manager.broadcast_sync))


def _verify_project(project_id: str, conn: sqlite3.Connection = Depends(get_db)) -> str:
    svc = ProjectService(conn)
    if svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Project {project_id} not found"
        })
    return project_id


@router.get("", response_model=list[SceneResponse])
def list_scenes(
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> list[SceneResponse]:
    return service.list_scenes(project_id)


@router.post("", response_model=list[SceneResponse], status_code=201)
def create_scenes(
    body: CreateScenesRequest,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> list[SceneResponse]:
    try:
        return service.create_scenes_from_script(project_id, body.script_version_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "type": "validation_error", "message": str(e)
        })


@router.delete("", status_code=204)
def delete_all_scenes(
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> None:
    service.delete_all_scenes(project_id)


@router.post("/clear-cache")
def clear_stock_cache(
    project_id: str = Depends(_verify_project),
) -> dict:
    """Purge all cached stock footage downloads (Pexels, Pixabay, Wikimedia, composed)."""
    return VisualService.clear_stock_cache()


@router.post("/add", response_model=SceneResponse, status_code=201)
def add_scene(
    body: SceneCreate,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> SceneResponse:
    return service.add_scene(project_id, body)


@router.delete("/{scene_id}", status_code=204)
def delete_scene(
    scene_id: int,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> None:
    if not service.delete_scene(scene_id):
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Scene {scene_id} not found"
        })


@router.patch("/{scene_id}", response_model=SceneResponse)
def update_scene(
    scene_id: int,
    data: SceneUpdate,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> SceneResponse:
    result = service.update_scene(scene_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Scene {scene_id} not found"
        })
    return result

@router.post("/{scene_id}/suggest-keywords", response_model=SuggestKeywordsResponse)
def suggest_keywords(
    scene_id: int,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> SuggestKeywordsResponse:
    """Generate context-aware keyword suggestions for a stock footage scene."""
    try:
        result = service.suggest_keywords(project_id, scene_id)
        return SuggestKeywordsResponse(
            suggestions=[
                KeywordSuggestionResponse(
                    keyword=s.keyword,
                    rank=s.rank,
                    original_term=s.original_term,
                    visual_synonym=s.visual_synonym,
                    category=s.category,
                    source_hints=s.source_hints,
                )
                for s in result.suggestions
            ],
            aesthetic_hints=result.aesthetic_hints,
            keyword_categories=result.keyword_categories,
            narrative_beats=[
                NarrativeBeatResponse(
                    beat=b.beat,
                    timestamp_hint=b.timestamp_hint,
                    suggested_keywords=b.suggested_keywords,
                )
                for b in result.narrative_beats
            ],
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": msg})
        raise HTTPException(status_code=422, detail={"type": "validation_error", "message": msg})



@router.post("/{scene_id}/search-footage")
def search_footage(
    scene_id: int,
    body: SearchFootageRequest,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> list[FootageResult] | list[WikimediaImageResult] | list[PixabayVideoResult] | list[UnsplashPhotoResult] | list:
    if body.source == "all":
        return service.search_all_sources(body.query)
    if body.source == "unsplash":
        return service.search_unsplash(body.query)
    if body.source == "wikimedia":
        return service.search_wikimedia(body.query)
    if body.source == "pixabay":
        return service.search_pixabay(body.query)
    return service.search_footage(body.query)


@router.post("/{scene_id}/select-footage", response_model=SceneResponse)
def select_footage(
    scene_id: int,
    body: SelectFootageRequest,
    project_id: str = Depends(_verify_project),
    service: VisualService = Depends(_get_visual_service),
) -> SceneResponse:
    # Build update — always set stock_video_path
    update = SceneUpdate(stock_video_path=body.stock_video_path)

    # Always merge source + stock_title into visual_data
    existing = service.get_scene(scene_id)
    if existing is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Scene {scene_id} not found"
        })
    merged_data = dict(existing.visual_data) if existing.visual_data else {}
    merged_data["source"] = body.source
    if body.stock_title:
        merged_data["stock_title"] = body.stock_title
    if body.attribution:
        merged_data["wikimedia_attribution"] = body.attribution
    update.visual_data = merged_data

    result = service.update_scene(scene_id, update)
    if result is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Scene {scene_id} not found"
        })
    return result


@router.post("/{scene_id}/render", status_code=202)
def render_scene(
    scene_id: int,
    background_tasks: BackgroundTasks,
    project_id: str = Depends(_verify_project),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Kick off scene render in background. Returns immediately with scene_id."""
    # Verify scene exists
    svc = VisualService(conn, job_runner=JobRunner(conn, broadcast=ws_manager.broadcast_sync))
    scene = svc.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail={
            "type": "not_found", "message": f"Scene {scene_id} not found"
        })

    # Mark as RUNNING immediately so the UI can show spinner
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "UPDATE scenes SET status = 'RUNNING', updated_at = ? WHERE id = ?",
            (now, scene_id),
        )
        conn.commit()
    except sqlite3.OperationalError:
        # DB may be busy from concurrent renders — not fatal, background task will proceed
        pass

    def _do_render() -> None:
        import sqlite3 as _sqlite3
        from studio_api.dependencies import get_db_path
        bg_conn = _sqlite3.connect(get_db_path(), timeout=30)
        bg_conn.row_factory = _sqlite3.Row
        bg_conn.execute("PRAGMA journal_mode=WAL")
        bg_conn.execute("PRAGMA busy_timeout=30000")
        try:
            bg_svc = VisualService(bg_conn, job_runner=JobRunner(bg_conn, broadcast=ws_manager.broadcast_sync))
            bg_svc.render_scene(project_id, scene_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Background render failed for scene %s", scene_id)
        finally:
            bg_conn.close()

    background_tasks.add_task(_do_render)
    return {"scene_id": scene_id, "status": "RUNNING"}


@router.get("/{scene_id}/preview")
def preview_scene(
    scene_id: int,
    project_id: str,
):
    """Serve rendered video or thumbnail for a scene."""
    import sqlite3 as _sqlite3
    from studio_api.dependencies import get_db_path
    conn = _sqlite3.connect(get_db_path(), timeout=30)
    conn.row_factory = _sqlite3.Row
    try:
        proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if proj is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": f"Project {project_id} not found"})
        row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": f"Scene {scene_id} not found"})

        # Prefer rendered video, fall back to thumbnail
        file_path = row["rendered_path"] or row["thumbnail_path"]
        if not file_path or not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail={"type": "not_found", "message": "No rendered file available"})

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        media_types = {"mp4": "video/mp4", "webm": "video/webm", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
        media_type = media_types.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type=media_type,
            headers={"Cache-Control": "no-store, must-revalidate", "Content-Length": str(len(content))},
        )
    finally:
        conn.close()

