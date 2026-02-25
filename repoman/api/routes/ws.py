"""WebSocket routes for real-time pipeline event streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job(websocket: WebSocket, job_id: str) -> None:
    """Stream real-time events for a pipeline job.

    Subscribes to the event bus and forwards all events to the client.
    Auto-reconnects if the client disconnects.

    Args:
        websocket: The WebSocket connection.
        job_id: Job identifier (used for context).
    """
    await websocket.accept()
    event_bus = websocket.app.state.event_bus
    queue = event_bus.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event))
            except TimeoutError:
                await websocket.send_text(json.dumps({"event": "ping", "data": {}}))
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(queue)
