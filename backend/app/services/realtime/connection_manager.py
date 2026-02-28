"""
@file connection_manager.py
@brief Tracks active WebSocket and SSE connections per user.

Thread-safe via asyncio locks.  Used by both the WebSocket endpoint and
the pub/sub subscriber to route messages to the correct connections.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol
from uuid import UUID

import structlog

from app.core.metrics import sse_connections_active, ws_connections_active

logger = structlog.get_logger(__name__)


class Sendable(Protocol):
    """@brief Protocol for objects that can send JSON data (WebSocket or SSE wrapper)."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """@brief Send a JSON-serializable dict to the client."""
        ...


class SSEConnection:
    """
    @brief Wrapper around an asyncio.Queue that conforms to :class:`Sendable`.

    The SSE endpoint reads from the queue and writes to the HTTP response stream.

    @param user_id UUID of the authenticated user.
    """

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def send_json(self, data: dict[str, Any]) -> None:
        """@brief Enqueue a message for SSE delivery."""
        await self.queue.put(data)


class ConnectionManager:
    """
    @brief Central registry of active realtime connections.

    Maintains a per-user set of :class:`Sendable` connections (WebSocket
    or SSE).  All mutations are guarded by an asyncio lock to prevent
    race conditions during concurrent connect/disconnect.
    """

    def __init__(self) -> None:
        self._connections: dict[UUID, set[Sendable]] = {}
        self._lock = asyncio.Lock()
        self._ws_count = 0
        self._sse_count = 0

    async def connect(self, conn: Sendable, user_id: UUID, *, is_sse: bool = False) -> None:
        """
        @brief Register a new connection for a user.

        @param conn The WebSocket or SSEConnection instance.
        @param user_id UUID of the authenticated user.
        @param is_sse Whether this is an SSE connection (for gauge tracking).
        """
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(conn)

            if is_sse:
                self._sse_count += 1
                sse_connections_active.set(self._sse_count)
            else:
                self._ws_count += 1
                ws_connections_active.set(self._ws_count)

        logger.debug("connection_added", user_id=str(user_id), is_sse=is_sse)

    async def disconnect(self, conn: Sendable, user_id: UUID, *, is_sse: bool = False) -> None:
        """
        @brief Remove a connection from tracking.

        @param conn The connection to remove.
        @param user_id UUID of the user.
        @param is_sse Whether this is an SSE connection.
        """
        async with self._lock:
            conns = self._connections.get(user_id)
            if conns:
                conns.discard(conn)
                if not conns:
                    del self._connections[user_id]

            if is_sse:
                self._sse_count = max(0, self._sse_count - 1)
                sse_connections_active.set(self._sse_count)
            else:
                self._ws_count = max(0, self._ws_count - 1)
                ws_connections_active.set(self._ws_count)

        logger.debug("connection_removed", user_id=str(user_id), is_sse=is_sse)

    async def send_to_user(self, user_id: UUID, message: dict[str, Any]) -> int:
        """
        @brief Send a message to all connections for a specific user.

        @param user_id Target user UUID.
        @param message JSON-serializable message dict.
        @return Number of connections the message was sent to.
        """
        async with self._lock:
            conns = self._connections.get(user_id)
            if not conns:
                return 0
            targets = list(conns)

        sent = 0
        for conn in targets:
            try:
                await conn.send_json(message)
                sent += 1
            except Exception:
                logger.debug("send_failed", user_id=str(user_id), exc_info=True)
        return sent

    async def broadcast(self, message: dict[str, Any]) -> int:
        """
        @brief Send a message to all connected users.

        @param message JSON-serializable message dict.
        @return Total number of connections the message was sent to.
        """
        async with self._lock:
            all_conns = [(uid, list(conns)) for uid, conns in self._connections.items()]

        sent = 0
        for _uid, conns in all_conns:
            for conn in conns:
                try:
                    await conn.send_json(message)
                    sent += 1
                except Exception:
                    pass
        return sent

    @property
    def connected_user_ids(self) -> set[UUID]:
        """@brief Return the set of currently connected user UUIDs."""
        return set(self._connections.keys())

    @property
    def total_connections(self) -> int:
        """@brief Return the total number of active connections across all users."""
        return sum(len(c) for c in self._connections.values())


manager = ConnectionManager()
"""@brief Singleton connection manager instance shared across the application."""
