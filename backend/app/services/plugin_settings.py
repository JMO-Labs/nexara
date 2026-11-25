"""
@file plugin_settings.py
@brief Pure helpers for plugin settings (secret masking/encryption) and user prefs.
"""

from __future__ import annotations

from typing import Any

from app.core.encryption import decrypt_secret, encrypt_secret
from app.plugins.manifest import FieldSpec, PluginManifest, validate_values, with_defaults


def mask_settings(manifest: PluginManifest, stored: dict[str, Any]) -> dict[str, Any]:
    """@return Settings with defaults; secret fields become ``{"set": bool}``."""
    out: dict[str, Any] = {}
    for k, f in manifest.settings.items():
        if f.type == "secret":
            out[k] = {"set": bool(stored.get(k))}
        elif k in stored or f.default is not None:
            out[k] = stored.get(k, f.default)
    return out


def merge_settings(
    manifest: PluginManifest, stored: dict[str, Any], patch: dict[str, Any], key: bytes
) -> dict[str, Any]:
    """
    @brief Validate ``patch`` and merge it over ``stored``.

    Secret values are Fernet-encrypted; an empty string for a secret keeps the old one.
    @raises AppError invalid_plugin_value (422).
    """
    specs: dict[str, FieldSpec] = manifest.settings
    blank = {k for k, v in patch.items() if v == "" and k in specs and specs[k].type == "secret"}
    clean = validate_values(specs, {k: v for k, v in patch.items() if k not in blank})
    merged = dict(stored)
    for k, v in clean.items():
        merged[k] = encrypt_secret(v, key) if specs[k].type == "secret" else v
    return merged


def decrypt_settings(
    manifest: PluginManifest, stored: dict[str, Any], key: bytes
) -> dict[str, Any]:
    """@return Plaintext settings (with defaults) for the plugin host. Never send to clients."""
    out = with_defaults(manifest.settings, {})
    for k, v in stored.items():
        spec = manifest.settings.get(k)
        if spec is None:
            continue
        out[k] = decrypt_secret(v, key) if spec.type == "secret" and v else v
    return out


def prefs_with_defaults(manifest: PluginManifest, stored: dict[str, Any]) -> dict[str, Any]:
    """@return User prefs; unset booleans default to off."""
    base = {k: False for k, f in manifest.user_prefs.items() if f.type == "boolean"}
    return {**base, **with_defaults(manifest.user_prefs, stored)}
