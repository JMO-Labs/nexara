"""
@file group_mapper.py
@brief Maps OAuth group claims to application roles.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

from app.schemas.subgroup import SUBGROUP_ROLES

if TYPE_CHECKING:
    from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository

logger = structlog.get_logger()

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


def _rules(claim_mapping: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """@brief Extract the optional group_mapping section (group -> rule dict)."""
    section = (claim_mapping or {}).get("group_mapping")
    if not isinstance(section, dict):
        return {}
    return {g: r for g, r in section.items() if isinstance(r, dict)}


def global_role_mappings(claim_mapping: dict[str, Any] | None) -> dict[str, str]:
    """
    @brief Group -> community role for rules without a subgroup_id.

    @param claim_mapping Provider claim_mapping (may hold group_mapping).
    @return Dict usable as group_mappings for map_groups_to_role.
    """
    return {
        g: str(r["role"])
        for g, r in _rules(claim_mapping).items()
        if not r.get("subgroup_id") and r.get("role")
    }


def has_subgroup_rules(claim_mapping: dict[str, Any] | None) -> bool:
    """@brief True when any group_mapping rule targets a subgroup (sync is active)."""
    return any(r.get("subgroup_id") for r in _rules(claim_mapping).values())


async def resolve_subgroup_mappings(
    subgroup_repo: SubgroupRepository,
    community_id: uuid.UUID,
    groups: list[str],
    claim_mapping: dict[str, Any] | None,
) -> dict[uuid.UUID, str]:
    """
    @brief Resolve group claims to existing local subgroups (no writes).

    Unmapped groups, invalid roles/ids and missing subgroups are skipped with a warning.

    @param subgroup_repo Subgroup repository.
    @param community_id Community scope.
    @param groups Group names from the token.
    @param claim_mapping Provider claim_mapping.
    @return subgroup_id -> subgroup role.
    """
    rules = _rules(claim_mapping)
    mapped: dict[uuid.UUID, str] = {}
    if not rules:
        return mapped
    for group in groups:
        rule = rules.get(group)
        if rule is None:
            logger.warning("oauth_group_unmapped", group=group)
            continue
        if not rule.get("subgroup_id"):
            continue
        role = str(rule.get("role") or "member")
        if role not in SUBGROUP_ROLES:
            logger.warning("oauth_group_invalid_role", group=group, role=role)
            continue
        try:
            sub_id = uuid.UUID(str(rule["subgroup_id"]))
        except ValueError:
            logger.warning("oauth_group_bad_subgroup_id", group=group)
            continue
        if await subgroup_repo.get_by_id(sub_id, community_id) is None:
            logger.warning("oauth_group_subgroup_missing", group=group, subgroup_id=str(sub_id))
            continue
        mapped[sub_id] = role
    return mapped


async def sync_subgroups(
    member_repo: SubgroupMemberRepository,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    mapped: dict[uuid.UUID, str],
) -> list[uuid.UUID]:
    """
    @brief Make the user's SSO memberships match ``mapped``.

    Adds missing memberships as source='sso', re-roles existing 'sso' rows,
    and deletes 'sso' rows not in ``mapped``. 'manual' rows are never touched.

    @param member_repo Subgroup member repository.
    @param community_id Community scope.
    @param user_id User being synced.
    @param mapped subgroup_id -> role from resolve_subgroup_mappings.
    @return Subgroup IDs the user was newly added to.
    """
    joined: list[uuid.UUID] = []
    for sub_id, role in mapped.items():
        row = await member_repo.get_membership(sub_id, user_id)
        if row is None:
            await member_repo.add_member(
                community_id=community_id,
                subgroup_id=sub_id,
                user_id=user_id,
                role=role,
                source="sso",
            )
            joined.append(sub_id)
        elif row.source == "sso" and row.role != role:
            await member_repo.update_role(row, role)
    for sub_id in await member_repo.list_sso_subgroup_ids(user_id, community_id):
        if sub_id not in mapped:
            await member_repo.remove_member(sub_id, user_id)
    return joined


async def apply_subgroup_mappings(
    subgroup_repo: SubgroupRepository,
    member_repo: SubgroupMemberRepository,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    groups: list[str],
    claim_mapping: dict[str, Any] | None,
) -> list[uuid.UUID]:
    """
    @brief Resolve the user's group claims and sync SSO subgroup memberships.

    No-op unless the provider has subgroup rules (so other providers' or
    manual memberships are never removed by an unmapped provider).

    @return Subgroup IDs the user was newly added to.
    """
    if not has_subgroup_rules(claim_mapping):
        return []
    mapped = await resolve_subgroup_mappings(subgroup_repo, community_id, groups, claim_mapping)
    return await sync_subgroups(member_repo, community_id, user_id, mapped)


async def preview_group_mapping(
    subgroup_repo: SubgroupRepository,
    community_id: uuid.UUID,
    claim_mapping: dict[str, Any] | None,
    sample_groups: list[str] | None,
) -> list[dict[str, Any]]:
    """
    @brief Resolve configured rules against local subgroups without writing.

    @param subgroup_repo Subgroup repository.
    @param community_id Community scope.
    @param claim_mapping Provider claim_mapping.
    @param sample_groups Optional group names to test the mapping with.
    @return One dict per configured group rule.
    """
    sample = set(sample_groups or [])
    out: list[dict[str, Any]] = []
    for group, rule in _rules(claim_mapping).items():
        raw = rule.get("subgroup_id")
        exists: bool | None = None
        if raw:
            try:
                exists = (
                    await subgroup_repo.get_by_id(uuid.UUID(str(raw)), community_id) is not None
                )
            except ValueError:
                exists = False
        out.append(
            {
                "group": group,
                "subgroup_id": str(raw) if raw else None,
                "role": rule.get("role"),
                "subgroup_exists": exists,
                "matched": group in sample,
            }
        )
    return out
