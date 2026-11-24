"""
@file test_sso_trust_and_guards.py
@brief trust_email (one application point + preset defaults), Entra xms_edov,
       update audit fields, last-admin role guard, subgroup sync audit.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.oauth_provider import OAuthProvider
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.schemas.oauth import OAuthProviderCreate
from app.services.auth.pending_link import create_link
from app.services.oauth.claim_mapper import map_claims
from app.services.oauth.flow import apply_email_trust
from app.services.oauth.group_mapper import sync_subgroups
from app.services.oauth.presets import PRESETS
from app.services.oauth.provider_rules import trust_email_for, update_audit
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
from tests.unit.services.oauth.helpers import sso_provider

UP = "app.services.oauth.user_provisioner."
PL = "app.services.auth.pending_link."


# ── trust_email ──────────────────────────────────────────────────────────


async def test_trust_on_marks_email_verified():
    auth = OAuthAuthResult(sub="1", email="a@b.c", email_verified=False)
    await apply_email_trust(sso_provider(preset="authentik", trust_email=True), {}, auth)
    assert auth.email_verified is True


async def test_trust_off_leaves_unverified():
    auth = OAuthAuthResult(sub="1", email="a@b.c", email_verified=False)
    await apply_email_trust(sso_provider(preset="authentik", trust_email=False), {}, auth)
    assert auth.email_verified is False


async def test_trust_without_email_stays_unverified():
    auth = OAuthAuthResult(sub="1", email=None, email_verified=False)
    await apply_email_trust(sso_provider(trust_email=True), {}, auth)
    assert auth.email_verified is False


async def test_github_ignores_trust_and_uses_api():
    auth = OAuthAuthResult(sub="1", email="victim@x.com", email_verified=True)
    with patch("app.services.oauth.flow.fetch_verified_email", AsyncMock(return_value=None)):
        await apply_email_trust(
            sso_provider(preset="github", trust_email=True), {"access_token": "t"}, auth
        )
    assert auth.email is None and auth.email_verified is False


@pytest.mark.parametrize(
    ("preset", "trusted"),
    [("authentik", True), ("keycloak", True), ("authelia", True), ("custom", True),
     ("google", False), ("microsoft", False), ("gitlab", False), ("github", False),
     ("discord", False)],
)  # fmt: skip
def test_preset_trust_defaults(preset, trusted):
    assert PRESETS[preset].trust_email is trusted
    assert PRESETS[preset].to_dict(preset)["trust_email"] is trusted


def _body(**kw) -> OAuthProviderCreate:
    base = {"slug": "x", "display_name": "X", "provider_type": "oidc", "client_id": "c"}
    return OAuthProviderCreate(**base, client_secret="s", **kw)


def test_create_takes_preset_default_explicit_wins():
    assert trust_email_for(_body(preset="authentik")) is True
    assert trust_email_for(_body(preset="authentik", trust_email=False)) is False
    assert trust_email_for(_body(preset="google")) is False
    assert trust_email_for(_body(preset="google", trust_email=True)) is True
    assert trust_email_for(_body()) is False


# ── Microsoft Entra: verified-email claim name is mappable ─────────────────


def test_entra_xms_edov_maps_to_email_verified():
    mapping = PRESETS["microsoft"].claim_mapping
    assert mapping["email_verified"] == "xms_edov"
    out = map_claims({"sub": "s", "email": "a@corp.com", "xms_edov": True}, mapping)
    assert out.email_verified is True
    out = map_claims({"sub": "s", "email": "a@corp.com"}, mapping)
    assert out.email_verified is False
    assert "xms_edov" in PRESETS["microsoft"].help


def test_default_mapping_still_reads_email_verified():
    assert map_claims({"sub": "s", "email_verified": "true"}, {}).email_verified is True


# ── update audit ───────────────────────────────────────────────────────────


def test_update_audit_lists_fields_and_security_values_without_secret():
    provider = MagicMock(spec=OAuthProvider)
    provider.allowed_domains, provider.required_group = ["corp.com"], "users"
    provider.trust_email, provider.auto_create_users = False, False
    provider.claim_mapping = {"group_mapping": {"a": {"role": "member"}}}
    data = {
        "allowed_domains": [],
        "required_group": None,
        "trust_email": True,
        "auto_create_users": True,
        "claim_mapping": {"group_mapping": {"a": {"role": "admin"}}},
        "client_secret_encrypted": "ENC",
        "display_name": "N",
    }
    out = update_audit(provider, data, secret=True)
    assert out["fields"] == [
        "allowed_domains", "auto_create_users", "claim_mapping", "display_name",
        "required_group", "trust_email", "client_secret",
    ]  # fmt: skip
    assert out["allowed_domains"] == {"old": ["corp.com"], "new": []}
    assert out["required_group"] == {"old": "users", "new": None}
    assert out["trust_email"] == {"old": False, "new": True}
    assert out["group_mapping"]["new"] == {"a": {"role": "admin"}}
    assert "ENC" not in repr(out)


# ── last-admin guard ─────────────────────────────────────────────────────


def _admin() -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.community_id, u.role, u.is_active = uuid.uuid4(), uuid.uuid4(), "admin", True
    return u


async def _returning_login(user, admins: int):
    link = MagicMock(user_id=user.id, email_from_provider=None, avatar_url=None)
    links, users = AsyncMock(), AsyncMock()
    links.find_by_provider_and_sub.return_value = link
    users.get_by_id.return_value = user
    users.count_active_admins.return_value = admins
    skipped, synced = AsyncMock(), AsyncMock()
    provider = sso_provider(group_mappings={"admins": "admin"}, sync_profile=False)
    with (
        patch(UP + "UserOAuthLinkRepository", return_value=links),
        patch(UP + "UserRepository", return_value=users),
        patch(UP + "audit_role_sync_skipped", skipped),
        patch(UP + "audit_role_synced", synced),
    ):
        auth = OAuthAuthResult(sub="s", email="a@b.c", email_verified=True, groups=[])
        await UserProvisioner(AsyncMock(), user.community_id).provision_user(
            auth, provider, "member"
        )
    return users, skipped, synced


async def test_sole_admin_not_demoted_by_sso():
    user = _admin()
    users, skipped, synced = await _returning_login(user, admins=1)
    users.update.assert_not_called()
    synced.assert_not_called()
    assert skipped.await_args.args[2:4] == ("admin", "member")


async def test_admin_demoted_when_another_admin_exists():
    user = _admin()
    users, skipped, synced = await _returning_login(user, admins=2)
    users.update.assert_awaited_once_with(user, {"role": "member"})
    skipped.assert_not_called()


async def test_held_link_does_not_demote_last_admin():
    user = _admin()
    links, users = AsyncMock(), AsyncMock()
    links.find_by_provider_and_sub.return_value = None
    users.get_by_id.return_value = user
    users.count_active_admins.return_value = 1
    skipped = AsyncMock()
    with (
        patch(PL + "UserOAuthLinkRepository", return_value=links),
        patch(PL + "UserRepository", return_value=users),
        patch(PL + "audit_role_sync_skipped", skipped),
    ):
        link = {"provider_id": str(uuid.uuid4()), "sub": "s", "role": "member"}
        await create_link(AsyncMock(), user.id, link)
    users.update.assert_not_called()
    skipped.assert_awaited_once()


# ── subgroup sync audit ───────────────────────────────────────────────────


async def test_subgroup_sync_audits_changes():
    a, b, gone = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    row_b = MagicMock(spec=SubgroupMember, source="sso", role="member")
    rows = {b: row_b, gone: MagicMock(spec=SubgroupMember, source="sso", role="member")}
    repo = AsyncMock(spec=SubgroupMemberRepository)
    repo.get_membership.side_effect = lambda s, u: rows.get(s)
    repo.list_sso_subgroup_ids.return_value = [b, gone]
    audit = AsyncMock()
    with patch("app.services.oauth.role_sync.AuditRepository") as audit_cls:
        audit_cls.return_value.append = audit
        pid = uuid.uuid4()
        await sync_subgroups(
            repo, uuid.uuid4(), uuid.uuid4(), {a: "member", b: "moderator"},
            session=AsyncMock(), provider_id=pid,
        )  # fmt: skip
    extra = audit.await_args.kwargs["extra_data"]
    assert audit.await_args.kwargs["action"] == "sso.subgroups_synced"
    assert extra == {"added": [str(a)], "removed": [str(gone)], "changed": [str(b)],
                     "provider_id": str(pid)}  # fmt: skip


async def test_subgroup_sync_without_change_not_audited():
    repo = AsyncMock(spec=SubgroupMemberRepository)
    repo.get_membership.return_value = None
    repo.list_sso_subgroup_ids.return_value = []
    with patch("app.services.oauth.role_sync.AuditRepository") as audit_cls:
        await sync_subgroups(repo, uuid.uuid4(), uuid.uuid4(), {}, session=AsyncMock())
    audit_cls.assert_not_called()
