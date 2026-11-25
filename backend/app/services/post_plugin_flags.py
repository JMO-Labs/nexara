"""
@file post_plugin_flags.py
@brief Validate per-plugin composer flags on a new post against enabled plugins' manifests.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError
from app.plugins.manifest import PluginManifest, validate_values, with_defaults
from app.repositories.plugin_repo import PluginRepository


def _invalid(detail: str) -> AppError:
    return AppError(
        code="invalid_plugin_flag",
        message="Invalid plugin flag",
        status_code=422,
        details={"errors": [detail]},
    )


async def validate_plugin_flags(
    repo: PluginRepository, community_id: uuid.UUID, flags: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """
    @brief Check flags against enabled plugins' ``composer_flags`` in the community.
    @param repo Plugin repository.
    @param community_id The author's community.
    @param flags ``{plugin_id: {flag: value}}`` from the request.
    @return The flags to store (only validated keys).
    Flags of plugins not enabled here are silently dropped. Untouched flags of enabled
    plugins are filled from manifest defaults (the composer shows them as pre-set).
    @raises AppError 422 ``invalid_plugin_flag`` for an unknown flag key or bad value.
    """
    allowed = {
        inst.plugin_id: PluginManifest.model_validate(inst.manifest).composer_flags
        for inst in await repo.list_enabled_installs(community_id)
    }
    out: dict[str, dict[str, Any]] = {}
    for plugin_id, values in flags.items():
        if plugin_id not in allowed:
            continue  # not installed/enabled/running here: dropped, the post still succeeds
        try:
            out[plugin_id] = with_defaults(
                allowed[plugin_id], validate_values(allowed[plugin_id], values)
            )
        except AppError as exc:
            raise _invalid(f"{plugin_id}: {exc.details}") from exc
    for plugin_id, fields in allowed.items():
        if plugin_id not in flags and (defaults := with_defaults(fields, {})):
            out[plugin_id] = defaults
    return out
