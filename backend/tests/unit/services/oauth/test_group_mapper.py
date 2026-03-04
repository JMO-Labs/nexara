"""
@file test_group_mapper.py
@brief Unit tests for OAuth group-to-role mapper.
"""

from app.services.oauth.group_mapper import map_groups_to_role


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
