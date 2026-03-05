"""Effects router — browse, filter, and manage the effect catalog."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from effects_catalog.catalog import EffectCatalog
from effects_catalog.exceptions import ConflictError, UnknownEffectError
from effects_catalog.legacy_mapper import LegacyMapper
from effects_catalog.models import EffectCategory
from effects_catalog.registry import EffectRegistry

router = APIRouter(prefix="/api/effects", tags=["effects"])

# Singleton registry — loaded once, reloadable
_catalog = EffectCatalog()
_mapper = LegacyMapper()
_registry = EffectRegistry(_catalog, legacy_mapper=_mapper)


# ── Pydantic models ─────────────────────────────────────────

class EffectSummary(BaseModel):
    identifier: str
    display_name: str
    category: str
    description: str


class EffectDetail(EffectSummary):
    parameter_schema: dict
    preview_config: dict
    reference_video_path: str
    sync_points: list[str]
    quality_profiles: dict
    initial_wait: float


class EffectCreateRequest(BaseModel):
    identifier: str
    display_name: str
    category: str
    description: str
    parameter_schema: dict = {}
    preview_config: dict = {}
    template_code: str = ""
    sync_points: list[str] = []
    quality_profiles: dict = {
        "draft": {"resolution": "720p", "fps": 15, "manim_quality": "-ql"},
        "production": {"resolution": "1080p", "fps": 30, "manim_quality": "-qh"},
    }


class AliasListResponse(BaseModel):
    aliases: dict[str, str]


# ── Endpoints ────────────────────────────────────────────────

@router.get("", response_model=list[EffectSummary])
def list_effects(category: str | None = None):
    """List all effects, optionally filtered by category."""
    cat = None
    if category:
        try:
            cat = EffectCategory(category)
        except ValueError:
            raise HTTPException(400, f"Invalid category '{category}'")
    return [
        EffectSummary(
            identifier=s.identifier,
            display_name=s.display_name,
            category=s.category.value,
            description=s.description,
        )
        for s in _registry.list_effects(category=cat)
    ]


@router.get("/aliases", response_model=AliasListResponse)
def list_aliases():
    """List legacy type → skeleton identifier mappings."""
    return AliasListResponse(aliases=_registry.list_aliases())


@router.get("/{identifier}", response_model=EffectDetail)
def get_effect(identifier: str):
    """Get full detail for a single effect."""
    try:
        s = _registry.resolve(identifier)
    except UnknownEffectError as exc:
        raise HTTPException(404, str(exc))
    return EffectDetail(
        identifier=s.identifier,
        display_name=s.display_name,
        category=s.category.value,
        description=s.description,
        parameter_schema=s.parameter_schema,
        preview_config=s.preview_config,
        reference_video_path=s.reference_video_path,
        sync_points=s.sync_points,
        quality_profiles=s.quality_profiles,
        initial_wait=s.initial_wait,
    )


@router.post("", response_model=EffectDetail, status_code=201)
def create_effect(req: EffectCreateRequest):
    """Save a new effect to the catalog (extraction workflow)."""
    from effects_catalog.models import EffectSkeleton

    try:
        cat = EffectCategory(req.category)
    except ValueError:
        raise HTTPException(400, f"Invalid category '{req.category}'")

    skeleton = EffectSkeleton(
        identifier=req.identifier,
        display_name=req.display_name,
        category=cat,
        description=req.description,
        parameter_schema=req.parameter_schema,
        preview_config=req.preview_config,
        sync_points=req.sync_points,
        quality_profiles=req.quality_profiles,
    )
    try:
        _catalog.save(skeleton)
        _registry.reload()
    except ConflictError as exc:
        raise HTTPException(409, str(exc))

    return EffectDetail(
        identifier=skeleton.identifier,
        display_name=skeleton.display_name,
        category=skeleton.category.value,
        description=skeleton.description,
        parameter_schema=skeleton.parameter_schema,
        preview_config=skeleton.preview_config,
        reference_video_path=skeleton.reference_video_path,
        sync_points=skeleton.sync_points,
        quality_profiles=skeleton.quality_profiles,
        initial_wait=skeleton.initial_wait,
    )
