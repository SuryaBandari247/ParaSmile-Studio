"""SQLite database helpers — connection factory, migration runner."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and foreign keys enabled."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def run_migrations(conn: sqlite3.Connection) -> None:
    """Execute all SQL migration files in order."""
    if not MIGRATIONS_DIR.exists():
        logger.warning("No migrations directory found at %s", MIGRATIONS_DIR)
        return

    # Ensure migration tracking table exists
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        "  filename TEXT PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )

    applied = {
        row["filename"]
        for row in conn.execute("SELECT filename FROM _migrations").fetchall()
    }

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for sql_file in sql_files:
        if sql_file.name in applied:
            continue
        logger.info("Applying migration: %s", sql_file.name)
        sql = sql_file.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _migrations (filename) VALUES (?)", (sql_file.name,)
        )
        conn.commit()
        logger.info("Migration applied: %s", sql_file.name)
