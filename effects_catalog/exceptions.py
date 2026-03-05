"""Custom exception hierarchy for the Effects Catalog."""

from __future__ import annotations


class EffectCatalogError(Exception):
    """Base exception for all effects catalog errors."""


class UnknownEffectError(EffectCatalogError):
    """Raised when an effect identifier is not found in the registry."""

    def __init__(self, identifier: str, available: list[str]):
        self.identifier = identifier
        self.available = available
        super().__init__(
            f"Effect '{identifier}' not found. "
            f"Available effects: {', '.join(sorted(available))}"
        )


class ConflictError(EffectCatalogError):
    """Raised when saving an effect with an identifier that already exists."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(
            f"Effect '{identifier}' already exists in the catalog"
        )


class SchemaValidationError(EffectCatalogError):
    """Raised when parameters violate an EffectSkeleton's JSON Schema."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        fields = [e.get("field", "unknown") for e in errors]
        super().__init__(
            f"Schema validation failed on fields: {', '.join(fields)}"
        )


class SyncPointMismatchError(EffectCatalogError):
    """Raised when audio timestamps count doesn't match sync_points count."""

    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Sync point mismatch: skeleton declares {expected} sync_points "
            f"but {actual} audio timestamps were provided"
        )


class UnknownProfileError(EffectCatalogError):
    """Raised when a requested quality profile doesn't exist."""

    def __init__(self, profile: str, available: list[str]):
        self.profile = profile
        self.available = available
        super().__init__(
            f"Quality profile '{profile}' not found. "
            f"Available profiles: {', '.join(sorted(available))}"
        )


class CatalogParseError(EffectCatalogError):
    """Raised when the catalog manifest contains malformed JSON."""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        loc = f" at position {position}" if position is not None else ""
        super().__init__(f"Catalog parse error{loc}: {message}")
