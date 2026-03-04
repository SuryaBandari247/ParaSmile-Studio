"""Studio API configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class StudioConfig:
    """Configuration loaded from environment variables with sensible defaults."""

    DATABASE_PATH: str = os.getenv("STUDIO_DB_PATH", ".data/studio.db")
    ARTIFACTS_DIR: str = os.getenv("STUDIO_ARTIFACTS_DIR", ".data/artifacts")
    HOST: str = os.getenv("STUDIO_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("STUDIO_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("STUDIO_LOG_LEVEL", "INFO")
    CORS_ORIGINS: list[str] = os.getenv(
        "STUDIO_CORS_ORIGINS", "http://localhost:5173"
    ).split(",")
