"""
@file sso_test_login.py
@brief Admin SSO test login: run a real IdP round-trip and report, never provision.

The admin starts a test (state stored in Valkey with the admin id); the shared
callback recognises the state, verifies the IdP response and calls
build_result(), which only reads: no user, link, membership, token or sign-in
row is written. The result is kept under a one-time key readable only by the
admin who started the test.
"""

from __future__ import annotations

import json
import secrets
import uuid
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.oauth_provider import OAuthProvider
from app.repositories.oauth_repo import OAuthProviderRepository, UserOAuthLinkRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.repositories.user_repo import UserRepository
from app.services.auth.policy import factor_methods
from app.services.oauth.flow import OAuthFlow
from app.services.oauth.group_mapper import (
    global_role_mappings,
    preview_group_mapping,
    resolve_subgroup_mappings,
)
from app.services.oauth.public_url import callback_url
from app.services.oauth.sso_rules import gate_refusal
from app.services.oauth.user_provisioner import OAuthAuthResult

CONTEXT_TTL = 600
"""@brief Seconds an admin has to finish the IdP login."""
RESULT_TTL = 300
"""@brief Seconds the result waits for the admin to read it (once)."""


def _ctx_key(state: str) -> str:
    return f"oauth_test:{state}"


def _result_key(result_id: str) -> str:
    return f"oauth_test_result:{result_id}"


async def load_provider(
    db: AsyncSession, community_id: uuid.UUID, provider_id: str
) -> OAuthProvider | None:
    """@brief Fresh (uncached) provider for a test context; enabled or not."""
    return await OAuthProviderRepository(db).get_by_id(uuid.UUID(provider_id), community_id)


async def start(
    valkey: Redis, settings: Settings, provider: OAuthProvider, admin_id: uuid.UUID
) -> str:
    """
    @brief Build the IdP authorize URL for a test login and remember its state.

    @param valkey Cache client.
    @param settings App settings (public base URL).
    @param provider Provider under test (may be disabled).
    @param admin_id Admin who started the test.
    @return Authorize URL to open in a popup.
    """
    nonce = secrets.token_urlsafe(32) if provider.provider_type == "oidc" else None
    url, state, verifier = OAuthFlow().build_authorize_url(
        provider, callback_url(settings, provider.slug), nonce=nonce
    )
    ctx = {
        "admin_id": str(admin_id),
        "provider_id": str(provider.id),
        "slug": provider.slug,
        "verifier": verifier,
        "nonce": nonce,
    }
    await valkey.setex(_ctx_key(state), CONTEXT_TTL, json.dumps(ctx))
    return url


async def consume_context(valkey: Redis, state: str) -> dict[str, Any] | None:
    """
    @brief Pop the test context for an OAuth state (single use).

    @param valkey Cache client.
    @param state ``state`` returned by the IdP.
    @return Context dict, or None when this is not a test login.
    """
    raw = await valkey.getdel(_ctx_key(state))
    if not isinstance(raw, str | bytes):
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


def _outcome(allowed: bool, action: str | None = None, code: str | None = None) -> dict[str, Any]:
    return {"allowed": allowed, "action": action, "code": code}


async def preview_outcome(
    db: AsyncSession, provider: OAuthProvider, auth_result: OAuthAuthResult
) -> dict[str, Any]:
    """
    @brief What a real sign-in would do, mirroring UserProvisioner (reads only).

    @return {allowed, action: sign_in|link|link_after_2fa|create|None, code: refusal|None}.
    """
    trusted = auth_result.email if auth_result.email_verified else None
    gate = gate_refusal(provider, trusted, auth_result.groups)
    if gate:
        return _outcome(False, code=gate)
    users = UserRepository(db)
    link = await UserOAuthLinkRepository(db).find_by_provider_and_sub(provider.id, auth_result.sub)
    if link is not None:
        linked = await users.get_by_id(link.user_id)
        if linked is None or not linked.is_active:
            return _outcome(False, code="sso_account_disabled")
        return _outcome(True, "sign_in")
    if not auth_result.email or not auth_result.email_verified:
        return _outcome(False, code="sso_email_unverified")
    user = await users.find_by_email(auth_result.email.strip().lower())
    if user is not None:
        if not user.is_active:
            return _outcome(False, code="sso_account_disabled")
        if not user.email_verified:
            return _outcome(False, code="sso_email_unverified_local")
        return _outcome(True, "link_after_2fa" if await factor_methods(db, user) else "link")
    if not provider.auto_create_users:
        return _outcome(False, code="sso_no_account")
    return _outcome(True, "create")


async def build_result(
    db: AsyncSession,
    community_id: uuid.UUID,
    provider: OAuthProvider,
    claims: dict[str, Any],
    auth_result: OAuthAuthResult,
    role: str,
) -> dict[str, Any]:
    """
    @brief Assemble the report: raw claims, mapped identity, role, groups, outcome.

    @param db Session (read only).
    @param community_id Community scope.
    @param provider Provider under test.
    @param claims Verified ID token / userinfo claims.
    @param auth_result Claims mapped to Nexara fields.
    @param role Community role the group mapping resolves to.
    @return JSON-serialisable result.
    """
    groups = auth_result.groups or []
    subs = SubgroupRepository(db)
    mapped = await resolve_subgroup_mappings(subs, community_id, groups, provider.claim_mapping)
    subgroups = []
    for sub_id, sub_role in mapped.items():
        sub = await subs.get_by_id(sub_id, community_id)
        subgroups.append({"id": str(sub_id), "name": sub.name if sub else "", "role": sub_role})
    return {
        "provider_id": str(provider.id),
        "claims": json.loads(json.dumps(claims, default=str)),
        "identity": {
            "sub": auth_result.sub,
            "email": auth_result.email,
            "email_verified": auth_result.email_verified,
            "display_name": auth_result.display_name,
            "username": auth_result.username,
            "groups": groups,
        },
        "role": role,
        "role_mapped": bool(
            provider.group_mappings or global_role_mappings(provider.claim_mapping)
        ),
        "subgroups": subgroups,
        "entries": await preview_group_mapping(subs, community_id, provider.claim_mapping, groups),
        "outcome": await preview_outcome(db, provider, auth_result),
    }


async def store_result(valkey: Redis, admin_id: str, result: dict[str, Any]) -> str:
    """
    @brief Keep a result for its admin under a one-time id.

    @return Result id (opaque, unguessable).
    """
    result_id = secrets.token_urlsafe(24)
    payload = json.dumps({"admin_id": admin_id, "result": result})
    await valkey.setex(_result_key(result_id), RESULT_TTL, payload)
    return result_id


async def read_result(valkey: Redis, result_id: str, admin_id: uuid.UUID) -> dict[str, Any] | None:
    """
    @brief Return and delete a result; only the admin who ran the test may read it.

    @return The result, or None when missing, expired, already read or not theirs.
    """
    raw = await valkey.getdel(_result_key(result_id))
    if not isinstance(raw, str | bytes):
        return None
    data = json.loads(raw)
    if data.get("admin_id") != str(admin_id):
        return None
    result = data.get("result")
    return result if isinstance(result, dict) else None
