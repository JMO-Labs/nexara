"""
@file list_user_pull_resolver.py
@brief Live, batched, privacy-gated resolution of ``user_pull`` list fields.

Sharing-pref mapping (no dedicated ``can_share_*`` columns exist):
- email / phone / address -> ``UserSettings.profile_visible_to == "community"``
- birthday               -> ``UserSettings.show_birthday_to == "community"``
A missing settings row uses the column server defaults (both ``"community"``),
matching ``birthday_repo``. The data owner must also have
``list_member.share_personal`` set, unless the viewer is the owner.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.models.user_settings import UserSettings
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository

_DEFAULT_TARGET = "item_user"
_PREF_FOR: dict[str, str] = {
    "email": "profile_visible_to",
    "phone": "profile_visible_to",
    "address": "profile_visible_to",
    "birthday": "show_birthday_to",
}
_DEFAULT_SCOPE = "community"

Result = dict[uuid.UUID, dict[str, Any]]


@dataclass(frozen=True)
class UserPullRepos:
    """@brief Repositories the resolver reads from (request-scoped)."""

    items: ListItemRepository
    users: UserRepository
    settings: SettingsRepository
    members: ListMemberRepository


class UserPullResolver:
    """@brief Resolves user_pull fields for a set of items.

    One instance per request; cached results expire after ``cache_ttl``
    seconds so sharing prefs are never served stale beyond that bound.
    """

    def __init__(self, cache_ttl: int = 300) -> None:
        """@param cache_ttl Seconds a cached result stays valid."""
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple[Any, ...], tuple[float, Result]] = {}

    @staticmethod
    def _allowed(field: str, prefs: UserSettings | None) -> bool:
        """@brief Owner's sharing pref for ``field``; missing row = defaults."""
        scope = getattr(prefs, _PREF_FOR[field], _DEFAULT_SCOPE) if prefs else _DEFAULT_SCOPE
        return bool(scope == _DEFAULT_SCOPE)

    def _cached(self, key: tuple[Any, ...]) -> Result | None:
        """@brief Return a fresh cached result or None (evicting stale)."""
        hit = self._cache.get(key)
        if hit is None:
            return None
        if time.monotonic() - hit[0] > self.cache_ttl:
            del self._cache[key]
            return None
        return hit[1]

    async def resolve(
        self,
        item_ids: list[uuid.UUID],
        list_id: uuid.UUID,
        field_schema: list[dict[str, Any]],
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        repos: UserPullRepos,
    ) -> Result:
        """@brief Resolve user_pull values.

        @return {item_id: {field_key: value}}; value is None when restricted,
                blocked, out of community or missing.
        """
        pulls = [f for f in field_schema if f.get("type") == "user_pull"]
        if not pulls or not item_ids:
            return {}
        ck = (list_id, viewer_id, community_id, tuple(item_ids))
        if (hit := self._cached(ck)) is not None:
            return hit

        items = await repos.items.get_many(list_id, item_ids, community_id)
        user_ids = {uid for it in items for f in pulls if (uid := self._target(it, f))}
        found = await repos.users.get_many(user_ids, community_id, viewer_id=viewer_id)
        users = {u.id: u for u in found}
        rows = await repos.settings.get_many(user_ids, community_id)
        prefs = {s.user_id: s for s in rows}
        shared = {m.user_id: m.share_personal for m in await repos.members.list_members(list_id)}

        out: Result = {}
        for it in items:
            res: dict[str, Any] = {}
            for f in pulls:
                src = (f.get("config") or {}).get("pull_from", "")
                uid = self._target(it, f)
                user = users.get(uid) if uid else None
                ok = (
                    user is not None
                    and uid is not None
                    and src in _PREF_FOR
                    and (
                        uid == viewer_id
                        or (shared.get(uid, False) and self._allowed(src, prefs.get(uid)))
                    )
                )
                res[f["key"]] = getattr(user, src, None) if ok else None
            out[it.id] = res
        self._cache[ck] = (time.monotonic(), out)
        return out

    def _target(self, item: Any, field: dict[str, Any]) -> uuid.UUID | None:
        """@brief Target user id referenced by an item for a user_pull field."""
        key = (field.get("config") or {}).get("target_user_field") or _DEFAULT_TARGET
        return self._to_uuid(item.values.get(key))

    @staticmethod
    def _to_uuid(raw: Any) -> uuid.UUID | None:
        """@brief Parse a stored user id; None when absent/invalid."""
        try:
            return uuid.UUID(str(raw)) if raw else None
        except ValueError:
            return None
