"""
@file plugin.py
@brief Request/response schemas for the plugin admin and member APIs.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class UrlInstall(BaseModel):
    """@brief Install from a manifest URL; the admin approves the manifest's scopes."""

    source: Literal["url"]
    manifest_url: str
    endpoint_url: str
    approved_scopes: list[str]


class PackageInstall(BaseModel):
    """@brief Install a package tarball via the plugin host; scopes approved as for url."""

    source: Literal["package"]
    package_url: str = Field(max_length=2048)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    approved_scopes: list[str] = []


class IndexInstall(BaseModel):
    """@brief Install from a marketplace index entry (not yet supported)."""

    source: Literal["index"]


PluginInstallIn = Annotated[
    UrlInstall | PackageInstall | IndexInstall, Field(discriminator="source")
]


class PluginCredentials(BaseModel):
    """@brief Plaintext secrets, shown exactly once on first enable."""

    token: str
    webhook_secret: str
    community_id: uuid.UUID


class PluginCommunityOut(BaseModel):
    """@brief Per-community enablement state."""

    plugin_id: str
    enabled: bool
    bot_user_id: uuid.UUID | None = None
    settings: dict[str, Any] = {}
    credentials: PluginCredentials | None = None
    host_error: str | None = None
    """@brief Plugin host could not be told (``unreachable``); the change still applied."""


class PluginInstallOut(BaseModel):
    """@brief An installed plugin as seen by the instance owner."""

    id: uuid.UUID
    plugin_id: str
    name: str
    version: str
    status: str
    tier: str | None = None
    scopes: list[str]
    events: list[str]
    egress: list[str]
    enabled: bool = False
    bot_user_id: uuid.UUID | None = None
    settings_schema: dict[str, Any] = {}
    source: Literal["url", "package"] = "url"
    host_status: str | None = None
    """@brief Live plugin-host status (package installs), ``unreachable`` if the host is down."""
    host_error: str | None = None


class PluginLogsOut(BaseModel):
    """@brief Last plugin output lines from the host."""

    lines: list[str]


class PluginUiOut(BaseModel):
    """@brief What members see: prefs and composer flag specs only."""

    plugin_id: str
    name: str
    user_prefs: dict[str, Any]
    composer_flags: dict[str, Any]


class PluginSettingsIn(BaseModel):
    """@brief Community enable/settings patch."""

    enabled: bool | None = None
    settings: dict[str, Any] | None = None


class PluginValuesIn(BaseModel):
    """@brief Per-user preference values."""

    values: dict[str, Any]


class PluginUninstallIn(BaseModel):
    """@brief Uninstall options."""

    delete_content: bool = False
