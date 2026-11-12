"""
@file loader.py
@brief Discover, validate and register plugins from the plugins directory.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
import uuid
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin
from app.plugins.manifest import PluginManifest, load_manifest
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

DEFAULT_PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


def _import_module(plugin_dir: Path, manifest: PluginManifest) -> ModuleType | None:
    """
    @brief Import the plugin's backend entry file, if declared.
    @param plugin_dir Plugin directory.
    @param manifest Validated manifest.
    @return Imported module or None when no entry is declared.
    @throws ValueError if the entry path escapes the plugin directory.
    """
    rel = manifest.backend.routes
    if not rel:
        return None
    root = plugin_dir.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"invalid backend entry '{rel}'")
    name = "nexara_plugin_" + re.sub(r"\W", "_", manifest.id)
    init = root / "__init__.py"
    if path.parent == root and init.is_file():
        # Package mode: lets entry files use relative imports (``from . import x``).
        for mod in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
            del sys.modules[mod]
        pkg_spec = importlib.util.spec_from_file_location(
            name, init, submodule_search_locations=[str(root)]
        )
        if pkg_spec is None or pkg_spec.loader is None:
            raise ValueError(f"cannot import package '{manifest.id}'")
        pkg = importlib.util.module_from_spec(pkg_spec)
        sys.modules[name] = pkg
        pkg_spec.loader.exec_module(pkg)
        name = f"{name}.{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import '{rel}'")
    module = importlib.util.module_from_spec(spec)
    if "." in name:
        sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


async def load_plugins(
    app: FastAPI,
    session: AsyncSession,
    community_id: uuid.UUID,
    plugins_dir: Path | None = None,
) -> None:
    """
    @brief Load enabled plugins, alphabetically by id; never raises per-plugin.
    @param app FastAPI app receiving plugin routers.
    @param session DB session used to read enablement state.
    @param community_id Community whose plugin installs apply.
    @param plugins_dir Override of the plugins directory.
    """
    root = plugins_dir or DEFAULT_PLUGINS_DIR
    if not root.is_dir():
        logger.info("plugins dir missing: %s", root)
        return
    result = await session.execute(
        select(Plugin.id).where(
            Plugin.community_id == community_id,
            Plugin.is_enabled.is_(True),
            Plugin.deleted_at.is_(None),
        )
    )
    enabled = set(result.scalars().all())

    for plugin_dir in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name):
        pid = plugin_dir.name
        try:
            manifest = load_manifest(plugin_dir)
            if manifest.id != pid:
                raise ValueError(f"manifest id '{manifest.id}' != directory '{pid}'")
            if manifest.id not in enabled:
                logger.info("plugin %s skipped: not enabled", pid)
                continue
            module = _import_module(plugin_dir, manifest)
            PluginRegistry.register(manifest, module, app)
            register_hooks = getattr(module, "register_hooks", None)
            if callable(register_hooks):
                register_hooks(community_id, manifest)
            logger.info("plugin %s loaded (v%s)", pid, manifest.version)
        except Exception:
            logger.error("plugin %s failed to load; skipped", pid, exc_info=True)
