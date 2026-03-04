"""FastAPI dependency injection helpers."""

from __future__ import annotations

import sqlite3
from typing import Generator

from studio_api.config import StudioConfig
from studio_api.database import get_connection
from studio_api.services.project_service import ProjectService


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a per-request database connection.

    Each request gets its own connection so that concurrent threads
    (FastAPI runs sync endpoints in a threadpool) never share SQLite
    connection state.  The connection is closed when the request ends.
    """
    conn = get_connection(StudioConfig.DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_db_path() -> str:
    """Return the database file path for creating new connections."""
    return StudioConfig.DATABASE_PATH


def get_project_service() -> Generator[ProjectService, None, None]:
    conn = get_connection(StudioConfig.DATABASE_PATH)
    try:
        yield ProjectService(conn)
    finally:
        conn.close()
