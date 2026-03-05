"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio_api.config import StudioConfig
from studio_api.database import get_connection, run_migrations
from studio_api.models.script_schema import ScriptSchemaReference
from studio_api.routers import audio, effects, music, projects, quickstart, render, research, scripts, topics, visuals, websocket

logging.basicConfig(level=getattr(logging, StudioConfig.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running database migrations...")
    conn = get_connection(StudioConfig.DATABASE_PATH)
    run_migrations(conn)
    conn.close()
    logger.info("Studio API ready")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Video Production Studio",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=StudioConfig.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router)
    app.include_router(quickstart.router)
    app.include_router(research.router)
    app.include_router(topics.router)
    app.include_router(scripts.router)
    app.include_router(audio.router)
    app.include_router(visuals.router)
    app.include_router(effects.router)
    app.include_router(music.router)
    app.include_router(render.router)
    app.include_router(websocket.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/script-schema", response_model=ScriptSchemaReference, tags=["schema"])
    def script_schema() -> ScriptSchemaReference:
        """Returns the full script JSON schema with all enum values for visual types,
        chart types, transitions, emotions, etc."""
        return ScriptSchemaReference()

    return app


app = create_app()
