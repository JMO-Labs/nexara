"""
@file test_group_sync.py
@brief SSO subgroup sync: add/remove 'sso' memberships, never touch 'manual'.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.subgroup import SubgroupMember
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.services.auth.pending_link import create_link
from app.services.oauth.group_mapper import sync_subgroups

CID, UID = uuid.uuid4(), uuid.uuid4()
A, B, M = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _member(source: str, role: str = "member") -> MagicMock:
    m = MagicMock(spec=SubgroupMember)
    m.source, m.role = source, role
    return m


def _repo(rows: dict[uuid.UUID, MagicMock]) -> AsyncMock:
    repo = AsyncMock(spec=SubgroupMemberRepository)
    repo.get_membership.side_effect = lambda s, u: rows.get(s)
    repo.list_sso_subgroup_ids.return_value = [s for s, m in rows.items() if m.source == "sso"]
    return repo


async def test_adds_missing_as_sso():
    repo = _repo({})
    await sync_subgroups(repo, CID, UID, {A: "moderator"})
    repo.add_member.assert_awaited_once_with(
        community_id=CID, subgroup_id=A, user_id=UID, role="moderator", source="sso"
    )


async def test_group_dropped_removes_sso_keeps_manual():
    repo = _repo({A: _member("sso"), M: _member("manual")})
    await sync_subgroups(repo, CID, UID, {})
    repo.remove_member.assert_awaited_once_with(A, UID)
    repo.list_sso_subgroup_ids.assert_awaited_once_with(UID, CID)


async def test_manual_membership_never_converted_or_rerolled():
    manual = _member("manual", role="owner")
    repo = _repo({M: manual})
    await sync_subgroups(repo, CID, UID, {M: "member"})
    repo.add_member.assert_not_called()
    repo.update_role.assert_not_called()
    repo.remove_member.assert_not_called()


async def test_sso_role_updated_when_mapping_changes():
    row = _member("sso", role="member")
    repo = _repo({B: row})
    await sync_subgroups(repo, CID, UID, {B: "moderator"})
    repo.update_role.assert_awaited_once_with(row, "moderator")
    repo.remove_member.assert_not_called()


async def test_held_link_syncs_subgroups_after_2fa():
    """pending_link reuses sync_subgroups once the link is created."""
    links = AsyncMock()
    links.find_by_provider_and_sub.return_value = None
    users = AsyncMock()
    users.get_by_id.return_value = MagicMock(id=UID, community_id=CID, role="member")
    sync = AsyncMock()
    link = {"provider_id": str(uuid.uuid4()), "sub": "s", "subgroups": {str(A): "member"}}
    with (
        patch("app.services.auth.pending_link.UserOAuthLinkRepository", return_value=links),
        patch("app.services.auth.pending_link.UserRepository", return_value=users),
        patch("app.services.auth.pending_link.sync_subgroups", sync),
    ):
        await create_link(AsyncMock(), UID, link)
    links.create.assert_awaited_once()
    sync.assert_awaited_once()
    assert sync.await_args.args[1:] == (CID, UID, {A: "member"})


async def test_held_link_role_audited():
    links = AsyncMock()
    links.find_by_provider_and_sub.return_value = None
    users = AsyncMock()
    users.get_by_id.return_value = MagicMock(id=UID, community_id=CID, role="member")
    audit = AsyncMock()
    pid = uuid.uuid4()
    with (
        patch("app.services.auth.pending_link.UserOAuthLinkRepository", return_value=links),
        patch("app.services.auth.pending_link.UserRepository", return_value=users),
        patch("app.services.auth.pending_link.audit_role_synced", audit),
    ):
        await create_link(AsyncMock(), UID, {"provider_id": str(pid), "sub": "s", "role": "admin"})
    audit.assert_awaited_once()
    assert audit.await_args.args[1:] == (UID, "member", "admin")


async def test_held_link_carries_subgroups_not_synced_at_callback():
    """First link to a 2FA account: mapped subgroups ride in pending_link."""
    from app.models.subgroup import Subgroup
    from app.models.user import User
    from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
    from tests.unit.services.oauth.helpers import sso_provider

    up = "app.services.oauth.user_provisioner."
    user = MagicMock(spec=User)
    user.id, user.role, user.is_active = UID, "member", True
    links, users, subs = AsyncMock(), AsyncMock(), AsyncMock()
    links.find_by_provider_and_sub.return_value = None
    users.find_by_email.return_value = user
    subs.get_by_id.return_value = MagicMock(spec=Subgroup)
    sync = AsyncMock()
    cm = {"group_mapping": {"eng": {"subgroup_id": str(A), "role": "member"}}}
    with (
        patch(up + "UserOAuthLinkRepository", return_value=links),
        patch(up + "UserRepository", return_value=users),
        patch(up + "SubgroupRepository", return_value=subs),
        patch(up + "factor_methods", AsyncMock(return_value=["totp"])),
        patch(up + "apply_subgroup_mappings", sync),
    ):
        p = UserProvisioner(AsyncMock(), CID)
        await p.provision_user(
            OAuthAuthResult(sub="s", email="a@b.c", email_verified=True, groups=["eng"]),
            sso_provider(claim_mapping=cm),
            "member",
        )
    assert p.pending_link is not None and p.pending_link["subgroups"] == {str(A): "member"}
    sync.assert_not_called()
    links.create.assert_not_called()
