"""Content Store — SQLite-backed persistence for pipeline artifacts."""

from content_store.exceptions import ContentStoreError


def __getattr__(name: str):
    if name == "ContentStore":
        from content_store.store import ContentStore

        return ContentStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ContentStore", "ContentStoreError"]
