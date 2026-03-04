"""WebSocket router — per-project real-time job status updates."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per project."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)
        logger.info("WebSocket connected for project %s (%d total)",
                     project_id, len(self._connections[project_id]))

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        if project_id in self._connections:
            self._connections[project_id] = [
                ws for ws in self._connections[project_id] if ws is not websocket
            ]
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info("WebSocket disconnected for project %s", project_id)

    async def broadcast(self, project_id: str, message: dict) -> None:
        """Send message to all connections for a project."""
        if project_id not in self._connections:
            return
        dead: list[WebSocket] = []
        for ws in self._connections[project_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(project_id, ws)

    def broadcast_sync(self, project_id: str, message: dict) -> None:
        """Synchronous broadcast wrapper for use from service layer.

        Schedules the async broadcast on the running event loop.
        Falls back to no-op if no event loop is running.
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(project_id, message))
        except RuntimeError:
            # No running event loop — skip broadcast
            pass

    def get_connection_count(self, project_id: str) -> int:
        return len(self._connections.get(project_id, []))

    def get_all_project_ids(self) -> list[str]:
        return list(self._connections.keys())


# Singleton manager
manager = ConnectionManager()


@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str) -> None:
    await manager.connect(project_id, websocket)
    try:
        while True:
            # Keep connection alive, handle client messages (ping/pong)
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
