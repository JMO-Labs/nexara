"""
@file hooks.py
@brief Event hook registry for plugins.

Events and the kwargs passed to handlers (after the leading ``ctx``):

- ``before_post_created(user_id, content, subgroup_id)``
- ``after_post_created(user_id, post_id, content, subgroup_id)``
- ``before_chat_sent(user_id, channel_id, content)``
- ``after_chat_sent(user_id, channel_id, message_id, content)``
- ``on_user_joined(user_id)`` — new member registered (local or OAuth)
- ``on_community_created(user_id)`` — ``user_id`` is the creating owner

Every event also receives the emit-level ``community_id`` and ``session`` via ``ctx``
(``PluginContext``); ``emit`` is called with ``community_id``, ``session`` and ``user_id``.

Handlers are ``async def handler(ctx: PluginContext, **kwargs)``. A plugin must list the
event in ``manifest.hooks`` and hold the ``hooks_<event>`` permission.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from app.plugins.context import PluginContext
from app.plugins.manifest import PluginManifest, PluginPermission

logger = logging.getLogger(__name__)

HOOK_EVENTS: tuple[str, ...] = (
    "before_post_created",
    "after_post_created",
    "before_chat_sent",
    "after_chat_sent",
    "on_user_joined",
    "on_community_created",
)
HANDLER_TIMEOUT = 30.0

Handler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class _Entry:
    plugin_id: str
    handler: Handler
    manifest: PluginManifest


class HookRegistry:
    """@brief Class-level singleton mapping events to plugin handlers."""

    _hooks: ClassVar[dict[tuple[uuid.UUID, str], list[_Entry]]] = {}

    @classmethod
    def register(
        cls,
        community_id: uuid.UUID,
        event_name: str,
        plugin_id: str,
        handler: Handler,
        manifest: PluginManifest,
    ) -> None:
        """
        @brief Register an async handler for an event in one community.
        @param community_id Community the plugin is installed in (tenant isolation).
        @throws ValueError for an unknown event or one not declared in manifest.hooks.
        """
        if event_name not in HOOK_EVENTS:
            raise ValueError(f"Unknown hook event '{event_name}'")
        if event_name not in manifest.hooks:
            raise ValueError(f"Plugin '{plugin_id}' does not declare hook '{event_name}'")
        cls._hooks.setdefault((community_id, event_name), []).append(
            _Entry(plugin_id, handler, manifest)
        )

    @classmethod
    async def emit(
        cls,
        event_name: str,
        *,
        community_id: uuid.UUID,
        session: Any,
        storage_client: Any = None,
        notification_service: Any = None,
        **kwargs: Any,
    ) -> list[Any]:
        """
        @brief Run the emitting community's handlers one after another; never raises.

        Handlers run sequentially because they share one AsyncSession (not
        concurrency-safe). Each runs in a SAVEPOINT so a failing plugin cannot
        abort the caller's transaction.
        @param community_id Community whose scoped PluginContext handlers receive.
        @param kwargs Event kwargs forwarded to handlers.
        @return Results of handlers that succeeded (skipped/failed/timed-out omitted).
        """
        entries = [
            e
            for e in cls._hooks.get((community_id, event_name), [])
            if PluginPermission(f"hooks_{event_name}") in e.manifest.permissions
        ]
        if not entries:
            return []

        async def run(e: _Entry) -> Any:
            ctx = PluginContext(
                e.plugin_id, e.manifest, session, community_id, storage_client, notification_service
            )
            if session is None:
                return await asyncio.wait_for(e.handler(ctx, **kwargs), HANDLER_TIMEOUT)
            async with session.begin_nested():
                return await asyncio.wait_for(e.handler(ctx, **kwargs), HANDLER_TIMEOUT)

        results: list[Any] = []
        for e in entries:
            try:
                results.append(await run(e))
            except Exception as exc:  # CancelledError is BaseException: propagates
                logger.error("Hook '%s' failed in plugin '%s': %r", event_name, e.plugin_id, exc)
        return results

    @classmethod
    def reset(cls) -> None:
        """@brief Clear all hooks (app startup / tests)."""
        cls._hooks.clear()
