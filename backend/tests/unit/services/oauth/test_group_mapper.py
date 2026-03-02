"""
@file test_group_mapper.py
@brief Tests for OAuth group-to-role mapping.
"""

from app.services.oauth.group_mapper import map_groups_to_role


class TestGroupMapper:
    """@brief Group-to-role mapping tests."""

    def test_single_admin_match(self):
        """@brief Single admin group maps to admin role."""
        mappings = {"idp-admins": "admin", "idp-members": "member"}
        assert map_groups_to_role(["idp-admins"], mappings, "member") == "admin"

    def test_single_member_match(self):
        """@brief Single member group maps to member role."""
        mappings = {"idp-admins": "admin", "idp-members": "member"}
        assert map_groups_to_role(["idp-members"], mappings, "viewer") == "member"

    def test_multiple_groups_highest_role_wins(self):
        """@brief Multiple groups: highest role wins."""
        mappings = {"admins": "admin", "members": "member", "viewers": "viewer"}
        assert map_groups_to_role(["viewers", "admins", "members"], mappings, "viewer") == "admin"

    def test_no_match_returns_default_role(self):
        """@brief No matching group returns default role."""
        mappings = {"admins": "admin"}
        assert map_groups_to_role(["other-group"], mappings, "member") == "member"

    def test_empty_groups_returns_default(self):
        """@brief Empty groups list returns default."""
        assert map_groups_to_role([], {"a": "admin"}, "viewer") == "viewer"

    def test_empty_mappings_returns_default(self):
        """@brief Empty mappings returns default."""
        assert map_groups_to_role(["some-group"], {}, "member") == "member"

    def test_viewer_mapping(self):
        """@brief Viewer mapping works."""
        mappings = {"readonly": "viewer"}
        assert map_groups_to_role(["readonly"], mappings, "member") == "viewer"

    def test_multiple_groups_member_beats_viewer(self):
        """@brief Member role beats viewer when both present."""
        mappings = {"team": "member", "guests": "viewer"}
        assert map_groups_to_role(["guests", "team"], mappings, "viewer") == "member"
