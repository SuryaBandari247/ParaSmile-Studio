"""EffectRegistry — runtime lookup replacing the hardcoded generators dict."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from effects_catalog.exceptions import UnknownEffectError
from effects_catalog.models import EffectCategory, EffectSkeleton

if TYPE_CHECKING:
    from effects_catalog.catalog import EffectCatalog
    from effects_catalog.legacy_mapper import LegacyMapper

logger = logging.getLogger(__name__)


class EffectRegistry:
    """Runtime index of all registered effect skeletons.

    Wraps EffectCatalog for fast lookup and integrates LegacyMapper
    for transparent backward compatibility with old scene type strings.
    """

    def __init__(
        self,
        catalog: EffectCatalog,
        legacy_mapper: LegacyMapper | None = None,
    ):
        self._catalog = catalog
        self._legacy_mapper = legacy_mapper
        self._index: dict[str, EffectSkeleton] = {}
        self.reload()

    def reload(self) -> None:
        """Re-index all skeletons from the catalog."""
        skeletons = self._catalog.load_all()
        self._index = {s.identifier: s for s in skeletons}
        logger.info("EffectRegistry loaded %d effects", len(self._index))

    def resolve(
        self, identifier: str, instruction: dict | None = None
    ) -> EffectSkeleton:
        """Return skeleton for identifier, checking LegacyMapper first.

        Raises UnknownEffectError listing available IDs if not found.
        """
        # Direct match
        if identifier in self._index:
            return self._index[identifier]

        # Try legacy alias resolution
        if self._legacy_mapper is not None:
            mapped = self._legacy_mapper.resolve(identifier, instruction)
            if mapped and mapped in self._index:
                return self._index[mapped]

        raise UnknownEffectError(identifier, list(self._index.keys()))

    def list_effects(
        self, category: EffectCategory | None = None
    ) -> list[EffectSkeleton]:
        """Return all skeletons, optionally filtered by category."""
        if category is None:
            return list(self._index.values())
        return [s for s in self._index.values() if s.category == category]

    def list_aliases(self) -> dict[str, str]:
        """Return the legacy alias table for the Effect Browser."""
        if self._legacy_mapper is None:
            return {}
        return self._legacy_mapper.list_aliases()
