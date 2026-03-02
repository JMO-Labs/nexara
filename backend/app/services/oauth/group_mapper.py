"""
@file group_mapper.py
@brief Maps OAuth/OIDC group claims to application roles.

Pure function: given user groups and a mapping dict, returns the
highest-priority role (admin > member > viewer).
"""

from __future__ import annotations

_ROLE_PRIORITY = {"admin": 3, "member": 2, "viewer": 1}


def map_groups_to_role(
    groups: list[str],
    mappings: dict[str, str],
    default_role: str,
) -> str:
    """
    @brief Map user groups to a single application role.

    Iterates through the user's groups, looks up each in the mappings dict,
    and returns the highest-priority role found. Role priority: admin > member > viewer.

    @param groups List of group names from the IdP (e.g. from groups claim).
    @param mappings Dict mapping IdP group names to role strings.
    @param default_role Role to return when no group matches.
    @return The resolved role string.
    """
    if not groups or not mappings:
        return default_role

    best_priority = 0
    result: str | None = None

    for group in groups:
        role = mappings.get(group)
        if role is None:
            continue
        priority = _ROLE_PRIORITY.get(role, 0)
        if priority > best_priority:
            best_priority = priority
            result = role

    return result if result is not None else default_role
