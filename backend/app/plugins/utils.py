"""@file utils.py
@brief Plugin directory validation and safe module naming.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ValidationError
from app.core.i18n import _
from app.plugins.manifest import PluginManifest, load_manifest

PLUGIN_ID_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_plugin_id(plugin_id: str) -> str:
    """
    @brief Check a plugin id against ``PLUGIN_ID_RE``.
    @return The id unchanged.
    @throws ValidationError if malformed.
    """
    if not PLUGIN_ID_RE.fullmatch(plugin_id):
        raise ValidationError(message=_("Invalid plugin id"))
    return plugin_id


def validate_plugin_dir(plugin_dir: Path) -> PluginManifest:
    """
    @brief Validate a plugin directory structure and read its manifest.
    @param plugin_dir Directory with manifest.toml/json and __init__.py.
    @return The validated manifest.
    @throws ValidationError on missing files, invalid manifest or bad id.
    """
    plugin_dir = Path(plugin_dir)
    if not plugin_dir.is_dir():
        raise ValidationError(message=_("Plugin directory not found"))
    if not (plugin_dir / "__init__.py").is_file():
        raise ValidationError(message=_("Plugin must contain __init__.py"))
    try:
        manifest = load_manifest(plugin_dir)
    except FileNotFoundError:
        raise ValidationError(
            message=_("Plugin must contain manifest.toml or manifest.json")
        ) from None
    except (PydanticValidationError, ValueError) as exc:
        raise ValidationError(
            message=_("Invalid plugin manifest"), details={"error": str(exc)}
        ) from exc
    validate_plugin_id(manifest.id)
    return manifest


def get_plugin_module_name(plugin_id: str) -> str:
    """
    @brief Build a safe Python module name for a plugin id.
    @throws ValidationError if the id is malformed.
    """
    return "plugin_" + validate_plugin_id(plugin_id).replace("-", "_")
