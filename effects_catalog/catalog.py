"""EffectCatalog — file-based persistence for effect skeletons."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from effects_catalog.exceptions import CatalogParseError, ConflictError
from effects_catalog.models import EffectCategory, EffectSkeleton

logger = logging.getLogger(__name__)


class EffectCatalog:
    """Persistent store for effect skeletons.

    Layout on disk:
        effects_catalog/
        ├── manifest.json          # Array of skeleton metadata
        ├── legacy_mappings.json   # Alias table for deprecated types
        ├── templates/             # Manim template modules
        └── assets/                # Reference video MP4s
    """

    def __init__(self, catalog_dir: str | Path = "effects_catalog"):
        self._dir = Path(catalog_dir)
        self._manifest_path = self._dir / "manifest.json"
        self._templates_dir = self._dir / "templates"
        self._assets_dir = self._dir / "assets"

    # ── Loading ──────────────────────────────────────────────

    def load_all(self) -> list[EffectSkeleton]:
        """Load and deserialize all skeletons from manifest.json."""
        if not self._manifest_path.exists():
            logger.warning("Manifest not found at %s — returning empty catalog", self._manifest_path)
            return []

        raw = self._manifest_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CatalogParseError(str(exc), position=exc.pos) from exc

        if not isinstance(data, list):
            raise CatalogParseError("Manifest root must be a JSON array")

        skeletons: list[EffectSkeleton] = []
        for i, entry in enumerate(data):
            try:
                skeleton = self.deserialize(entry)
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Skipping malformed entry %d in manifest: %s", i, exc)
                continue

            # Warn on missing template module file (non-fatal)
            if skeleton.template_module:
                tpl_path = self._templates_dir / f"{skeleton.template_module.split('.')[-1]}.py"
                if not tpl_path.exists():
                    logger.warning(
                        "Template module '%s' not found at %s — skeleton '%s' loaded anyway",
                        skeleton.template_module, tpl_path, skeleton.identifier,
                    )

            # Warn on missing reference video (non-fatal)
            if skeleton.reference_video_path:
                vid_path = self._dir / skeleton.reference_video_path
                if not vid_path.exists():
                    logger.warning(
                        "Reference video not found at %s for skeleton '%s'",
                        vid_path, skeleton.identifier,
                    )

            skeletons.append(skeleton)

        return skeletons

    def get_by_id(self, identifier: str) -> EffectSkeleton | None:
        """Return a single skeleton by identifier, or None."""
        for skeleton in self.load_all():
            if skeleton.identifier == identifier:
                return skeleton
        return None

    # ── Saving ───────────────────────────────────────────────

    def save(self, skeleton: EffectSkeleton) -> None:
        """Persist a new skeleton to the catalog. Raises ConflictError if ID exists."""
        existing = self.load_all()
        ids = {s.identifier for s in existing}
        if skeleton.identifier in ids:
            raise ConflictError(skeleton.identifier)

        existing.append(skeleton)
        self._write_manifest(existing)

    def _write_manifest(self, skeletons: list[EffectSkeleton]) -> None:
        """Write the full manifest to disk."""
        data = [self.serialize(s) for s in skeletons]
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ── Serialization ────────────────────────────────────────

    @staticmethod
    def serialize(skeleton: EffectSkeleton) -> dict:
        """Convert EffectSkeleton to a JSON-serializable dict."""
        return {
            "identifier": skeleton.identifier,
            "display_name": skeleton.display_name,
            "category": skeleton.category.value if isinstance(skeleton.category, EffectCategory) else skeleton.category,
            "description": skeleton.description,
            "parameter_schema": skeleton.parameter_schema,
            "preview_config": skeleton.preview_config,
            "reference_video_path": skeleton.reference_video_path,
            "template_module": skeleton.template_module,
            "sync_points": skeleton.sync_points,
            "quality_profiles": skeleton.quality_profiles,
            "initial_wait": skeleton.initial_wait,
        }

    @staticmethod
    def deserialize(data: dict) -> EffectSkeleton:
        """Convert a JSON dict back to an EffectSkeleton."""
        return EffectSkeleton(
            identifier=data["identifier"],
            display_name=data["display_name"],
            category=EffectCategory(data["category"]),
            description=data["description"],
            parameter_schema=data.get("parameter_schema", {}),
            preview_config=data.get("preview_config", {}),
            reference_video_path=data.get("reference_video_path", ""),
            template_module=data.get("template_module", ""),
            sync_points=data.get("sync_points", []),
            quality_profiles=data.get("quality_profiles", {
                "draft": {"resolution": "720p", "fps": 15, "manim_quality": "-ql", "encoder": "libx264"},
                "production": {"resolution": "1080p", "fps": 30, "manim_quality": "-qh", "encoder": "h264_videotoolbox"},
            }),
            initial_wait=data.get("initial_wait", 0.0),
        )
