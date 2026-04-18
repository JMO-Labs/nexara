"""
@file group_mapper.py
@brief Maps OAuth group claims to application roles.
"""

from __future__ import annotations

# Role priority: higher index = higher priority.

_ROLE_PRIORITY = ("viewer", "member", "admin")


def map_groups_to_role(
    groups: list[str],
    group_mappings: dict[str, str],
    default_role: str,
) -> str:
    """
    @brief Map user groups to an application role.

    Checks if any user group matches a mapping and returns the
    highest-priority role (admin > member > viewer). Falls back
    to default_role when no mapping matches.

    @param groups List of group names from the OAuth provider.
    @param group_mappings Dict mapping group name -> role (e.g. {"admin": "admin"}).
    @param default_role Role to use when no mapping matches.
    @return The resolved role string.
    """
    best_role: str | None = None
    best_priority = -1

    for group in groups:
        if group in group_mappings:
            role = group_mappings[group]
            try:
                idx = _ROLE_PRIORITY.index(role)
            except ValueError:
                idx = -1
            if idx > best_priority:
                best_priority = idx
                best_role = role

    return best_role if best_role is not None else default_role
