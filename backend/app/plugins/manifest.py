"""@file Plugin manifest schema and loader.

@brief Pydantic models validating ``manifest.toml`` / ``manifest.json``.
Permissions are declared here but enforced in PluginContext, not at this layer.
"""

import json
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class PluginPermission(StrEnum):
    """@brief Permissions a plugin may request.

    - ``db_read``: read access to the plugin's scoped data.
    - ``db_write``: write access to the plugin's scoped data.
    - ``hooks_before_post_created``: intercept posts before creation.
    - ``hooks_after_post_created``: react after a post is created.
    - ``hooks_before_chat_sent`` / ``hooks_after_chat_sent``: chat message hooks.
    - ``hooks_on_user_joined`` / ``hooks_on_community_created``: membership/community hooks.
    - ``send_notifications``: send notifications to users.
    - ``storage_access``: use the file/object storage.
    - ``external_http``: make outbound HTTP requests.
    - ``frontend_routes``: register frontend routes/slots.
    - ``celery_tasks``: register background Celery tasks.
    """

    DB_READ = "db_read"
    DB_WRITE = "db_write"
    HOOKS_BEFORE_POST_CREATED = "hooks_before_post_created"
    HOOKS_AFTER_POST_CREATED = "hooks_after_post_created"
    HOOKS_BEFORE_CHAT_SENT = "hooks_before_chat_sent"
    HOOKS_AFTER_CHAT_SENT = "hooks_after_chat_sent"
    HOOKS_ON_USER_JOINED = "hooks_on_user_joined"
    HOOKS_ON_COMMUNITY_CREATED = "hooks_on_community_created"
    SEND_NOTIFICATIONS = "send_notifications"
    STORAGE_ACCESS = "storage_access"
    EXTERNAL_HTTP = "external_http"
    FRONTEND_ROUTES = "frontend_routes"
    CELERY_TASKS = "celery_tasks"


def _check_semver(value: str) -> str:
    """@brief Require strict MAJOR.MINOR.PATCH.
    @param value Version string.
    @return The same string if valid.
    """
    parts = value.split(".")
    if len(parts) != 3 or not all(p.isascii() and p.isdigit() for p in parts):
        raise ValueError(f"'{value}' is not a valid semantic version (MAJOR.MINOR.PATCH)")
    try:
        Version(value)
    except InvalidVersion as exc:
        raise ValueError(str(exc)) from exc
    return value


class ManifestHook(BaseModel):
    """@brief A hook event name with its description."""

    event: str
    description: str = ""


class SettingSpec(BaseModel):
    """@brief Declaration of one plugin setting."""

    type: Literal["string", "integer", "boolean", "number"]
    label: str
    required: bool = False
    secret: bool = False


class BackendSpec(BaseModel):
    """@brief Backend entry files (relative paths)."""

    routes: str | None = None
    tasks: str | None = None


class FrontendSpec(BaseModel):
    """@brief Frontend slot name -> component name."""

    slots: dict[str, str] = Field(default_factory=dict)


class PluginManifest(BaseModel):
    """@brief Validated plugin manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str
    version: str
    author: str
    description: str
    min_core_version: str
    permissions: list[PluginPermission] = Field(default_factory=list)
    hooks: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, SettingSpec] = Field(default_factory=dict)
    backend: BackendSpec = Field(default_factory=BackendSpec)
    frontend: FrontendSpec = Field(default_factory=FrontendSpec)

    @field_validator("version", "min_core_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        return _check_semver(v)

    @field_validator("permissions")
    @classmethod
    def _unique_permissions(cls, v: list[PluginPermission]) -> list[PluginPermission]:
        if len(set(v)) != len(v):
            raise ValueError("duplicate permissions")
        return v


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [k for k, _ in pairs]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"duplicate keys in manifest: {sorted(dupes)}")
    return dict(pairs)


def load_manifest(plugin_dir: Path) -> PluginManifest:
    """@brief Load ``manifest.toml`` or ``manifest.json`` from a plugin dir.
    @param plugin_dir Plugin directory.
    @return Validated manifest.
    @throws FileNotFoundError if neither file exists.
    @throws pydantic.ValidationError on invalid content (duplicate JSON keys,
    e.g. duplicate hooks, are reported as a ValidationError too).
    """
    plugin_dir = Path(plugin_dir)
    toml_path = plugin_dir / "manifest.toml"
    json_path = plugin_dir / "manifest.json"
    if toml_path.is_file():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    elif json_path.is_file():
        try:
            data = json.loads(
                json_path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys
            )
        except ValueError as exc:
            raise ValidationError.from_exception_data(
                "PluginManifest",
                [{"type": "value_error", "loc": (), "input": None, "ctx": {"error": exc}}],
            ) from exc
    else:
        raise FileNotFoundError(f"No manifest.toml or manifest.json in {plugin_dir}")
    return PluginManifest.model_validate(data)


def is_compatible(manifest: PluginManifest, core_version: str) -> bool:
    """@brief Check core version >= manifest.min_core_version.
    @param manifest Plugin manifest.
    @param core_version Running core version.
    @return True if compatible.
    """
    return Version(core_version) >= Version(manifest.min_core_version)
