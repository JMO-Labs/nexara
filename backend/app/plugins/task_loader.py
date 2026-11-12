"""
@file task_loader.py
@brief Import plugin Celery task modules (``manifest.backend.tasks``) in worker/beat.

Importing a tasks module registers its ``@celery_app.task`` functions and lets it
add entries to ``celery_app.conf.beat_schedule``. Only plugins holding the
``celery_tasks`` permission are imported. Enablement is per community and lives in
the DB, so tasks must check it themselves when they run.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.plugins import loader
from app.plugins.manifest import PluginPermission, load_manifest

logger = logging.getLogger(__name__)


def plugins_root() -> Path:
    """@brief Directory scanned for plugins (same as the API loader)."""
    return loader.DEFAULT_PLUGINS_DIR


def load_plugin_tasks(plugins_dir: Path | None = None) -> list[str]:
    """
    @brief Import every valid plugin's tasks module; never raises per plugin.
    @param plugins_dir Override of the plugins directory.
    @return Ids of plugins whose tasks were imported, alphabetically.
    """
    root = plugins_dir or plugins_root()
    loaded: list[str] = []
    if not root.is_dir():
        logger.info("plugins dir missing: %s", root)
        return loaded
    for plugin_dir in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name):
        try:
            manifest = load_manifest(plugin_dir)
            if manifest.id != plugin_dir.name:
                raise ValueError(f"manifest id '{manifest.id}' != directory '{plugin_dir.name}'")
            rel = manifest.backend.tasks
            if not rel:
                continue
            if PluginPermission.CELERY_TASKS not in manifest.permissions:
                logger.warning("plugin %s tasks skipped: lacks celery_tasks", manifest.id)
                continue
            loader.import_entry(plugin_dir, manifest, rel, fresh=False)
            loaded.append(manifest.id)
        except Exception:
            logger.error("plugin %s tasks failed to load; skipped", plugin_dir.name, exc_info=True)
    return loaded
