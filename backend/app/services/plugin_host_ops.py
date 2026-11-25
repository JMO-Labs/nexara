"""
@file plugin_host_ops.py
@brief PluginService part for host-run (package) plugins: install, env push, best-effort
       stop/delete, live status and logs.
"""

from __future__ import annotations

import structlog

from app.core.exceptions import AppError
from app.models.plugin import PluginInstall
from app.plugins.package import fetch_package_manifest
from app.schemas.plugin import PackageInstall, PluginInstallOut
from app.services.plugin_base import PluginServiceBase
from app.services.plugin_host_client import HostPluginStatus, PluginHostClient, not_configured
from app.services.plugin_host_sync import endpoint_for, push_to_host

logger = structlog.get_logger(__name__)


def host_error_code(e: AppError) -> str:
    """@return UI error key for a host failure (``cleanup_failed`` | ``unreachable``)."""
    return "cleanup_failed" if e.code == "plugin_host_cleanup_failed" else "unreachable"


class PluginHostOps(PluginServiceBase):
    """@brief Plugin-host side of PluginService."""

    def _host(self) -> PluginHostClient:
        return PluginHostClient.from_settings(self._settings)

    async def _install_package(self, body: PackageInstall) -> PluginInstallOut:
        """
        @brief Verify the package and record the install. No community is enabled and the
            host is not contacted until the first enable.
        @raises AppError ``plugin_host_not_configured`` (422), ``package_sha256_mismatch``,
            ``invalid_manifest``, ``scopes_not_approved``.
        """
        if not self._settings.PLUGIN_HOST_URL:
            raise not_configured()
        m = await fetch_package_manifest(body.package_url, body.sha256)
        await self._review(m, body.approved_scopes)
        inst = await self._repo.create_install(
            plugin_id=m.id,
            version=m.version,
            manifest=m.model_dump(mode="json"),
            package_url=body.package_url,
            sha256=body.sha256.lower(),
            endpoint_url=endpoint_for(self._settings, m.id),
            granted_scopes=list(m.scopes),
            status="disabled",
        )
        await self._log(
            "plugin.installed", m.id, {"version": m.version, "scopes": m.scopes, "package": True}
        )
        return await self._out(inst)

    async def _sync_host(self, inst: PluginInstall, strict: bool) -> str | None:
        """
        @brief Push the install's env to the host (or stop it when nothing is enabled).
        @param strict Raise on host failure (enable / settings: the change rolls back).
            Otherwise log and return the UI error key (disable: revocation already done
            in Nexara; the poll reconciles the host).
        @return None on success.
        """
        if not self._settings.PLUGIN_HOST_URL:
            if strict:
                raise not_configured()
            return None
        try:
            await push_to_host(self._repo, inst, self._key, self._settings, self._host())
        except AppError as e:
            if strict:
                raise
            logger.warning("plugin_host.sync_failed", plugin_id=inst.plugin_id, code=e.code)
            return host_error_code(e)
        return None

    async def _host_delete(self, inst: PluginInstall, purge: bool) -> str | None:
        """@brief Best-effort host DELETE; returns the UI error key on failure."""
        if not inst.package_url or not self._settings.PLUGIN_HOST_URL:
            return None
        try:
            await self._host().delete(inst.plugin_id, purge=purge)
        except AppError as e:
            logger.warning("plugin_host.delete_failed", plugin_id=inst.plugin_id, code=e.code)
            return host_error_code(e)
        return None

    async def list_installed(self) -> list[PluginInstallOut]:
        """@brief All installs with this community's enablement and live host status."""
        installs = await self._repo.list_installs()
        host: dict[str, HostPluginStatus] = {}
        if self._settings.PLUGIN_HOST_URL and any(i.package_url for i in installs):
            try:
                host = {r.id: r for r in await self._host().status()}
            except AppError:
                host = {
                    i.plugin_id: HostPluginStatus(id=i.plugin_id, status="unreachable")
                    for i in installs
                    if i.package_url
                }
        return [await self._out(i, host) for i in installs]

    async def logs(self, plugin_id: str, lines: int = 200) -> list[str]:
        """@brief Last output lines of a package plugin from the host (url installs: none)."""
        inst = await self._install(plugin_id)
        if not inst.package_url:
            return []
        return await self._host().logs(plugin_id, lines)
