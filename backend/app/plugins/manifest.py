"""
@file
@brief Plugin manifest (nexara-plugin.toml) parser and field validation.
"""

import re
import tomllib
from typing import Any, Literal

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppError

KNOWN_SCOPES = frozenset(
    "posts:read posts:write comments:read comments:write reactions:write "
    "media:read users:read notifications:send".split()
)
KNOWN_EVENTS = frozenset({"post.created", "comment.created", "mention"})
_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")


class FieldSpec(BaseModel):
    """@brief One configurable field (setting, user pref or composer flag)."""

    type: Literal["boolean", "select", "number", "string", "secret"]
    label: str
    help: str | None = None
    default: Any = None
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    max_length: int | None = None


class PluginManifest(BaseModel):
    """@brief Parsed and validated plugin manifest."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    min_core_version: str = "0.0.0"
    runtime: Literal["node", "python"]
    entrypoint: str
    icon: str | None = None
    bot_display_name: str
    bot_username: str
    bot_avatar: str | None = None
    scopes: list[str] = []
    events: list[str] = []
    egress: list[str] = []
    settings: dict[str, FieldSpec] = {}
    user_prefs: dict[str, FieldSpec] = {}
    composer_flags: dict[str, FieldSpec] = {}


def _fail(errors: list[str]) -> AppError:
    return AppError(
        code="invalid_manifest",
        message="Invalid plugin manifest",
        status_code=422,
        details={"errors": errors},
    )


def parse_manifest(text: str) -> PluginManifest:
    """
    @brief Parse nexara-plugin.toml text.
    @param text TOML source.
    @return Validated manifest.
    @throws AppError invalid_manifest (422) on any problem.
    """
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise _fail([f"toml: {exc}"]) from exc
    p, bot, perm = raw.get("plugin", {}), raw.get("bot", {}), raw.get("permissions", {})
    try:
        m = PluginManifest(
            **p,
            bot_display_name=bot.get("display_name"),
            bot_username=bot.get("username"),
            bot_avatar=bot.get("avatar"),
            scopes=perm.get("scopes", []),
            events=perm.get("events", []),
            egress=perm.get("egress", []),
            settings=raw.get("settings", {}),
            user_prefs=raw.get("user_prefs", {}),
            composer_flags=raw.get("composer_flags", {}),
        )
    except (ValidationError, TypeError) as exc:
        errs = (
            [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
            if isinstance(exc, ValidationError)
            else [str(exc)]
        )
        raise _fail(errs) from exc
    errors: list[str] = []
    if not _ID_RE.match(m.id):
        errors.append(f"id: invalid '{m.id}'")
    for label, ver in (("version", m.version), ("min_core_version", m.min_core_version)):
        if not _SEMVER_RE.match(ver):
            errors.append(f"{label}: not semver '{ver}'")
    errors += [f"scopes: unknown '{s}'" for s in m.scopes if s not in KNOWN_SCOPES]
    errors += [f"events: unknown '{e}'" for e in m.events if e not in KNOWN_EVENTS]
    for group in ("user_prefs", "composer_flags"):
        for k, f in getattr(m, group).items():
            if f.type == "secret":
                errors.append(f"{group}.{k}: secret only allowed in settings")
    for group in ("settings", "user_prefs", "composer_flags"):
        for k, f in getattr(m, group).items():
            if f.type == "select" and not f.options:
                errors.append(f"{group}.{k}: select needs options")
    if errors:
        raise _fail(errors)
    return m


def core_version() -> str:
    """@brief Running core version."""
    return str(get_settings().APP_VERSION)


def is_compatible(m: PluginManifest) -> bool:
    """@brief True if core version >= manifest min_core_version."""
    try:
        return Version(core_version()) >= Version(m.min_core_version)
    except InvalidVersion:
        return False


def _check(spec: FieldSpec, v: Any) -> bool:
    t = spec.type
    if t == "boolean":
        return isinstance(v, bool)
    if t == "select":
        return v in (spec.options or [])
    if t == "number":
        if isinstance(v, bool) or not isinstance(v, int | float):
            return False
        return (spec.min is None or v >= spec.min) and (spec.max is None or v <= spec.max)
    if not isinstance(v, str):
        return False
    return spec.max_length is None or len(v) <= spec.max_length


def validate_values(fields: dict[str, FieldSpec], values: dict[str, Any]) -> dict[str, Any]:
    """
    @brief Validate values against field specs.
    @param fields Field specs by key.
    @param values Candidate values.
    @return values unchanged when valid.
    @throws AppError invalid_plugin_value (422).
    """
    errors = [
        f"{k}: unknown key" if k not in fields else f"{k}: invalid value"
        for k, v in values.items()
        if k not in fields or not _check(fields[k], v)
    ]
    if errors:
        raise AppError(
            code="invalid_plugin_value",
            message="Invalid plugin value",
            status_code=422,
            details={"errors": errors},
        )
    return values


def with_defaults(fields: dict[str, FieldSpec], values: dict[str, Any]) -> dict[str, Any]:
    """@brief Return values with missing keys filled from non-null defaults."""
    out = {k: f.default for k, f in fields.items() if f.default is not None}
    return {**out, **values}
