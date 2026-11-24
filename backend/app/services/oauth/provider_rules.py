"""
@file provider_rules.py
@brief Pure helpers for admin provider writes: preset defaults, errors, update audit.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError
from app.core.i18n import _
from app.models.oauth_provider import OAuthProvider
from app.schemas.oauth import OAuthProviderCreate
from app.services.oauth.presets import PRESETS


def username_claim_for(body: OAuthProviderCreate) -> str:
    """@brief Explicit username_claim wins; else the preset's (github login, ...)."""
    if "username_claim" not in body.model_fields_set and body.preset in PRESETS:
        return PRESETS[body.preset].username_claim
    return body.username_claim


def trust_email_for(body: OAuthProviderCreate) -> bool:
    """@brief Explicit trust_email wins; else the preset's default (False without one)."""
    if body.trust_email is not None:
        return body.trust_email
    return PRESETS[body.preset].trust_email if body.preset in PRESETS else False


#: Fields whose old/new values are audited on update (security-relevant).
_AUDIT_VALUES = (
    "allowed_domains",
    "required_group",
    "auto_create_users",
    "trust_email",
    "default_role",
    "enabled",
)


def slug_taken() -> AppError:
    """@brief 409 sso_slug_taken (shown on the wizard's slug field)."""
    return AppError(
        code="sso_slug_taken",
        message=_("A provider with this slug already exists"),
        status_code=409,
        details={"field": "slug"},
    )


def invalid_discovery(exc: Exception) -> AppError:
    """@brief 422 invalid_discovery for a failed discovery fetch."""
    return AppError(code="invalid_discovery", message=str(exc), status_code=422)


def update_audit(provider: OAuthProvider, data: dict[str, Any], secret: bool) -> dict[str, Any]:
    """
    @brief Audit payload for an update: changed field names, old/new for gates and
           role grants; never secret values.
    """
    fields = sorted(k for k in data if k != "client_secret_encrypted")
    out: dict[str, Any] = {"fields": fields + (["client_secret"] if secret else [])}
    for key in _AUDIT_VALUES:
        if key in data:
            out[key] = {"old": getattr(provider, key), "new": data[key]}
    if "group_mappings" in data:
        out["group_mappings"] = {"old": provider.group_mappings, "new": data["group_mappings"]}
    if "claim_mapping" in data:
        old_cm, new_cm = provider.claim_mapping or {}, data["claim_mapping"] or {}
        out["group_mapping"] = {
            "old": old_cm.get("group_mapping"),
            "new": new_cm.get("group_mapping"),
        }
    return out
