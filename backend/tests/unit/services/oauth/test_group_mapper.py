"""
@file test_group_mapper.py
@brief Unit tests for OAuth group-to-role mapper.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.subgroup import Subgroup, SubgroupMember
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.oauth.group_mapper import (
    apply_subgroup_mappings,
    global_role_mappings,
    map_groups_to_role,
    preview_group_mapping,
)


class TestMapGroupsToRole:
    """@brief Tests for map_groups_to_role function."""

    def test_admin_group_maps_to_admin(self):
        """Admin group maps to admin when mapping exists."""
        result = map_groups_to_role(["admin-group"], {"admin-group": "admin"}, "member")
        assert result == "admin"

    def test_multiple_groups_resolves_to_highest_priority(self):
        """Multiple groups resolves to highest priority (admin > member)."""
        mappings = {"admins": "admin", "members": "member", "viewers": "viewer"}
        result = map_groups_to_role(["viewers", "members", "admins"], mappings, "viewer")
        assert result == "admin"

    def test_empty_groups_returns_default_role(self):
        """Empty groups returns default_role."""
        result = map_groups_to_role([], {"admin-group": "admin"}, "member")
        assert result == "member"

    def test_empty_mappings_returns_default_role(self):
        """Empty mappings returns default_role."""
        result = map_groups_to_role(["admin-group"], {}, "viewer")
        assert result == "viewer"

    def test_unknown_group_names_returns_default_role(self):
        """Unknown group names returns default_role."""
        result = map_groups_to_role(["unknown-group"], {"admin-group": "admin"}, "member")
        assert result == "member"

    def test_viewer_priority_lower_than_member(self):
        """Viewer priority is lower than member."""
        mappings = {"viewers": "viewer", "members": "member"}
        result = map_groups_to_role(["viewers", "members"], mappings, "viewer")
        assert result == "member"


ENG, DES = uuid.uuid4(), uuid.uuid4()
CID, UID = uuid.uuid4(), uuid.uuid4()
CM = {
    "group_mapping": {
        "eng": {"subgroup_id": str(ENG), "role": "member"},
        "design": {"subgroup_id": str(DES), "role": "moderator"},
        "admin": {"subgroup_id": None, "role": "admin"},
    }
}


def _repos(existing=(ENG, DES), member_of=()):
    subs = AsyncMock(spec=SubgroupRepository)
    subs.get_by_id.side_effect = lambda i, c: MagicMock(spec=Subgroup) if i in existing else None
    mem = AsyncMock(spec=SubgroupMemberRepository)
    mem.get_membership.side_effect = lambda s, u: (
        MagicMock(spec=SubgroupMember) if s in member_of else None
    )
    return subs, mem


class TestGlobalRoleMappings:
    """@brief Tests for global_role_mappings."""

    def test_only_entries_without_subgroup(self):
        assert global_role_mappings(CM) == {"admin": "admin"}

    def test_no_group_mapping_is_empty(self):
        assert global_role_mappings({"sub": "sub"}) == {}
        assert global_role_mappings(None) == {}


class TestApplySubgroupMappings:
    """@brief Tests for apply_subgroup_mappings."""

    async def test_multiple_groups_add_memberships_with_roles(self):
        subs, mem = _repos()
        joined = await apply_subgroup_mappings(subs, mem, CID, UID, ["eng", "design", "admin"], CM)
        assert set(joined) == {ENG, DES}
        roles = {c.kwargs["subgroup_id"]: c.kwargs["role"] for c in mem.add_member.call_args_list}
        assert roles == {ENG: "member", DES: "moderator"}

    async def test_missing_local_subgroup_skipped(self):
        subs, mem = _repos(existing=(DES,))
        joined = await apply_subgroup_mappings(subs, mem, CID, UID, ["eng", "design"], CM)
        assert joined == [DES]

    async def test_unmapped_group_skipped(self):
        subs, mem = _repos()
        assert await apply_subgroup_mappings(subs, mem, CID, UID, ["other"], CM) == []
        mem.add_member.assert_not_called()

    async def test_idempotent_when_already_member(self):
        subs, mem = _repos(member_of=(ENG,))
        joined = await apply_subgroup_mappings(subs, mem, CID, UID, ["eng"], CM)
        assert joined == []
        mem.add_member.assert_not_called()

    async def test_no_mapping_configured_noop(self):
        subs, mem = _repos()
        assert await apply_subgroup_mappings(subs, mem, CID, UID, ["eng"], {}) == []
        subs.get_by_id.assert_not_called()

    async def test_invalid_subgroup_id_skipped(self):
        subs, mem = _repos()
        cm = {"group_mapping": {"eng": {"subgroup_id": "nope", "role": "member"}}}
        assert await apply_subgroup_mappings(subs, mem, CID, UID, ["eng"], cm) == []


class TestPreview:
    """@brief Tests for preview_group_mapping (sandbox, no writes)."""

    async def test_reports_existence_and_match(self):
        subs, mem = _repos(existing=(ENG,))
        out = await preview_group_mapping(subs, CID, CM, ["eng"])
        by = {e["group"]: e for e in out}
        assert by["eng"] == {
            "group": "eng",
            "subgroup_id": str(ENG),
            "role": "member",
            "subgroup_exists": True,
            "matched": True,
        }
        assert by["design"]["subgroup_exists"] is False
        assert by["design"]["matched"] is False
        assert by["admin"]["subgroup_exists"] is None
        mem.add_member.assert_not_called()

    async def test_no_sample_groups_marks_none_matched(self):
        subs, _ = _repos()
        out = await preview_group_mapping(subs, CID, CM, None)
        assert not any(e["matched"] for e in out)
