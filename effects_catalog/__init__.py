"""
Effects Catalog — A catalog-driven, extensible library of animation effect skeletons.

Replaces the hardcoded generator dispatch in manim_codegen.py with a file-based
catalog (JSON manifest + Python templates + MP4 assets) that the registry loads
at startup and exposes through the API.
"""

__version__ = "0.1.0"

from effects_catalog.models import EffectCategory, EffectSkeleton
from effects_catalog.exceptions import (
    CatalogParseError,
    ConflictError,
    EffectCatalogError,
    SchemaValidationError,
    SyncPointMismatchError,
    UnknownEffectError,
    UnknownProfileError,
)

__all__ = [
    "EffectSkeleton",
    "EffectCategory",
    "EffectCatalogError",
    "UnknownEffectError",
    "ConflictError",
    "SchemaValidationError",
    "SyncPointMismatchError",
    "UnknownProfileError",
    "CatalogParseError",
]
