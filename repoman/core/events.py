"""Async event bus for real-time pipeline event streaming."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


class EventBus:
    """Simple async publish-subscribe event bus."""

    def __init__(self) -> None:
        """Initialise with empty listener and subscriber registries."""
        self._callbacks: dict[str, list[Callable[..., Any]]] = {}
        self._queues: list[asyncio.Queue[dict[str, Any]]] = []

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a callback for a named event.

        Args:
            event: Event name to listen for.
            callback: Async or sync callable invoked on emit.
        """
        self._callbacks.setdefault(event, []).append(callback)

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Create and register a new subscriber queue.

        Returns:
            Queue that receives all emitted events.
        """
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.append(q)
        return q

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue.

        Args:
            queue: The queue to deregister.
        """
        try:
            self._queues.remove(queue)
        except ValueError:
            pass

    async def emit(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all callbacks and subscriber queues.

        Args:
            event: Event name.
            data: Payload dictionary.
        """
        payload = {"event": event, "data": data}
        for callback in self._callbacks.get(event, []):
            result = callback(event, data)
            if asyncio.iscoroutine(result):
                await result
        for q in list(self._queues):
            await q.put(payload)
