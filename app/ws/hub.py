from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from fastapi import WebSocket


@dataclass
class Channel:
    # Simple in-memory broadcast channel
    name: str
    max_buffer: int = 500
    buffer: List[Dict[str, Any]] = field(default_factory=list)
    sockets: Set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, msg: Dict[str, Any]) -> None:
        async with self.lock:
            self.buffer.append(msg)
            if len(self.buffer) > self.max_buffer:
                self.buffer = self.buffer[-self.max_buffer:]
            dead = []
            for ws in self.sockets:
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.sockets.discard(ws)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.sockets.add(ws)
            for msg in self.buffer:
                await ws.send_json(msg)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self.lock:
            self.sockets.discard(ws)


class Hub:
    def __init__(self) -> None:
        self._channels: Dict[str, Channel] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Channel:
        async with self._lock:
            if key not in self._channels:
                self._channels[key] = Channel(name=key)
            return self._channels[key]


hub = Hub()
