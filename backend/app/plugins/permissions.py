"""@file permissions.py
@brief Permission enforcement for plugins against their manifest.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.manifest import PluginManifest, PluginPermission

if TYPE_CHECKING:
    from app.plugins.context import PluginContext


def enforce_permission(manifest: PluginManifest, permission: str | PluginPermission) -> None:
    """
    @brief Ensure the manifest declares a permission.
    @param manifest The plugin manifest.
    @param permission Permission name or enum member.
    @throws PermissionError if not declared (or unknown).
    """
    try:
        perm = PluginPermission(permission)
    except ValueError:
        raise PermissionError(f"Unknown plugin permission '{permission}'") from None
    if perm not in manifest.permissions:
        raise PermissionError(f"Plugin '{manifest.id}' does not have permission '{perm.value}'")


def check_permission(ctx: PluginContext, permission: str | PluginPermission) -> None:
    """@brief Enforce a permission for a PluginContext. @throws PermissionError"""
    enforce_permission(ctx.manifest, permission)
