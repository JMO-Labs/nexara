"""
@file test_user_provisioner_groups.py
@brief UserProvisioner group-mapping integration (subgroups + role sync).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner

MOD = "app.services.oauth.user_provisioner"
CM = {"group_mapping": {"ops": {"subgroup_id": None, "role": "admin"}}}


def _link_and_user(role="member"):
    link = MagicMock()
    link.user_id = uuid.uuid4()
    link.email_from_provider = "u@x.com"
    link.avatar_url = None
    user = MagicMock(spec=User)
    user.id = link.user_id
    user.role = role
    return link, user


async def _provision(claim_mapping, groups, role="admin", legacy=None):
    link, user = _link_and_user()
    link_repo, user_repo = AsyncMock(), AsyncMock()
    link_repo.find_by_provider_and_sub = AsyncMock(return_value=link)
    user_repo.get_by_id = AsyncMock(return_value=user)
    provider = MagicMock()
    provider.id = uuid.uuid4()
    provider.group_mappings = legacy or {}
    provider.claim_mapping = claim_mapping
    cid = uuid.uuid4()
    apply = AsyncMock(return_value=[])
    sub_repo, mem_repo = MagicMock(), MagicMock()
    with (
        patch(f"{MOD}.UserOAuthLinkRepository", return_value=link_repo),
        patch(f"{MOD}.UserRepository", return_value=user_repo),
        patch(f"{MOD}.SubgroupRepository", return_value=sub_repo),
        patch(f"{MOD}.SubgroupMemberRepository", return_value=mem_repo),
        patch(f"{MOD}.apply_subgroup_mappings", apply),
    ):
        result = await UserProvisioner(AsyncMock(), cid).provision_user(
            OAuthAuthResult(sub="s", email="u@x.com", groups=groups), provider, role
        )
    return result, user, user_repo, apply, (sub_repo, mem_repo, cid)


class TestProvisionerGroupMapping:
    """@brief provision_user hooks subgroup mapping and role sync."""

    async def test_applies_subgroup_mappings_with_token_groups(self):
        result, user, _, apply, (subs, mem, cid) = await _provision(CM, ["eng", "ops"])
        assert result is user
        apply.assert_awaited_once_with(subs, mem, cid, user.id, ["eng", "ops"], CM)

    async def test_role_synced_when_only_claim_mapping_group_mapping(self):
        _, user, user_repo, _, _ = await _provision(CM, ["ops"], role="admin")
        user_repo.update.assert_awaited_once_with(user, {"role": "admin"})

    async def test_role_not_synced_without_any_group_mapping(self):
        _, _, user_repo, _, _ = await _provision({}, ["ops"], role="admin")
        user_repo.update.assert_not_called()
