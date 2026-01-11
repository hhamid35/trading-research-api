"""WebSocket hub and channel for broadcasting messages to multiple clients."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Channel:
    """WebSocket channel for broadcasting messages to multiple clients.

    Maintains a buffer of recent messages and manages active connections.
    """

    name: str
    max_buffer: int = 500
    buffer: list[dict[str, Any]] = field(default_factory=list)
    sockets: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, msg: dict[str, Any]) -> None:
        """Broadcast message to all connected clients and add to buffer."""
        async with self.lock:
            self.buffer.append(msg)
            if len(self.buffer) > self.max_buffer:
                self.buffer = self.buffer[-self.max_buffer :]

            dead_sockets = []
            for ws in self.sockets:
                try:
                    await ws.send_json(msg)
                except Exception as e:
                    logger.warning("Failed to send message to websocket: %s", e)
                    dead_sockets.append(ws)

            for ws in dead_sockets:
                self.sockets.discard(ws)

    async def connect(self, ws: WebSocket) -> None:
        """Accept new WebSocket connection and replay buffered messages."""
        await ws.accept()
        async with self.lock:
            self.sockets.add(ws)
            for msg in self.buffer:
                try:
                    await ws.send_json(msg)
                except Exception as e:
                    logger.error("Failed to send buffered message: %s", e)
                    self.sockets.discard(ws)
                    raise

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove WebSocket from active connections."""
        async with self.lock:
            self.sockets.discard(ws)


class Hub:
    """Manages WebSocket channels for different sessions/jobs."""

    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Channel:
        """Get or create a channel for the given key."""
        async with self._lock:
            if key not in self._channels:
                self._channels[key] = Channel(name=key)
            return self._channels[key]


# Global hub instance shared across the application
hub = Hub()
