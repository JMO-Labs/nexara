"""
@file registry.py
@brief Process-wide registry of loaded plugins.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import ClassVar

from fastapi import APIRouter, FastAPI

from app.plugins.manifest import PluginManifest

PLUGIN_ROUTE_PREFIX = "/api/v1/plugins"


@dataclass(frozen=True)
class LoadedPlugin:
    """@brief A loaded plugin: its manifest and imported module (if any)."""

    manifest: PluginManifest
    module: ModuleType | None = None


class PluginRegistry:
    """@brief Class-level singleton store of loaded plugins."""

    _plugins: ClassVar[dict[str, LoadedPlugin]] = {}

    @classmethod
    def register(
        cls, manifest: PluginManifest, module: ModuleType | None, app: FastAPI | None = None
    ) -> LoadedPlugin:
        """
        @brief Store a plugin and mount its ``router`` if the module has one.
        @param manifest Validated manifest.
        @param module Imported plugin module or None.
        @param app App to mount the router on (skipped when None).
        @return The stored LoadedPlugin.
        """
        router = getattr(module, "router", None)
        if app is not None and isinstance(router, APIRouter):
            app.include_router(router, prefix=f"{PLUGIN_ROUTE_PREFIX}/{manifest.id}")
        loaded = LoadedPlugin(manifest=manifest, module=module)
        cls._plugins[manifest.id] = loaded
        return loaded

    @classmethod
    def get(cls, plugin_id: str) -> LoadedPlugin | None:
        """@brief Return a loaded plugin or None."""
        return cls._plugins.get(plugin_id)

    @classmethod
    def list(cls) -> list[LoadedPlugin]:
        """@brief Return all loaded plugins sorted by id."""
        return [cls._plugins[k] for k in sorted(cls._plugins)]

    @classmethod
    def reset(cls) -> None:
        """@brief Clear the registry (tests / reload)."""
        cls._plugins.clear()
