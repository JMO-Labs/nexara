"""
@file list_user_pull_resolver.py
@brief Live, batched, privacy-gated resolution of ``user_pull`` list fields.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import ListItem
from app.models.user import User
from app.models.user_settings import UserSettings

_DEFAULT_TARGET = "item_user"


class UserPullResolver:
    """@brief Resolves user_pull fields for a set of items.

    One instance per request: the internal cache makes repeated resolves reuse
    one snapshot of users/prefs, and a new request re-reads sharing prefs.
    """

    def __init__(self, cache_ttl: int = 300) -> None:
        """@param cache_ttl Upper bound (seconds) a cached snapshot is considered valid."""
        self.cache_ttl = cache_ttl
        self._cache: dict[Any, dict[str, Any]] = {}

    @staticmethod
    def _allowed(field: str, owner: User, prefs: UserSettings | None) -> bool:
        """@brief Per-field sharing pref of the data owner; restrictive by default."""
        if prefs is None:
            return False
        flag = getattr(prefs, f"can_share_{field}", None)
        if flag is None and field == "birthday":
            return getattr(prefs, "show_birthday_to", "nobody") not in ("nobody", "private")
        return bool(flag)

    async def resolve(
        self,
        item_ids: list[uuid.UUID],
        list_id: uuid.UUID,
        field_schema: list[dict[str, Any]],
        viewer_id: uuid.UUID,
        member_repo: Any,
        session: AsyncSession,
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """@brief Resolve user_pull values.

        @return {item_id: {field_key: value}}; value is None when restricted or missing.
        """
        pulls = [f for f in field_schema if f.get("type") == "user_pull"]
        if not pulls or not item_ids:
            return {}
        ck = (list_id, viewer_id, tuple(item_ids))
        if ck in self._cache:
            return self._cache[ck]  # type: ignore[return-value]

        items = (
            (await session.execute(select(ListItem).where(ListItem.id.in_(item_ids))))
            .scalars()
            .all()
        )
        targets: dict[uuid.UUID, uuid.UUID] = {}
        user_ids: set[uuid.UUID] = set()
        for it in items:
            for f in pulls:
                key = (f.get("config") or {}).get("target_user_field") or _DEFAULT_TARGET
                uid = self._to_uuid(it.values.get(key))
                if uid:
                    user_ids.add(uid)
        users: dict[uuid.UUID, User] = {}
        prefs: dict[uuid.UUID, UserSettings] = {}
        if user_ids:
            rows = await session.execute(select(User).where(User.id.in_(user_ids)))
            users = {u.id: u for u in rows.scalars().all()}
            rows = await session.execute(
                select(UserSettings).where(UserSettings.user_id.in_(user_ids))
            )
            prefs = {s.user_id: s for s in rows.scalars().all()}
        shared = {m.user_id: m.share_personal for m in await member_repo.list_members(list_id)}

        out: dict[uuid.UUID, dict[str, Any]] = {}
        for it in items:
            res: dict[str, Any] = {}
            for f in pulls:
                cfg = f.get("config") or {}
                src = cfg.get("pull_from", "")
                uid = self._to_uuid(it.values.get(cfg.get("target_user_field") or _DEFAULT_TARGET))
                user = users.get(uid) if uid else None
                ok = (
                    user is not None
                    and src in ("email", "phone", "address", "birthday")
                    and (
                        uid == viewer_id
                        or (shared.get(uid, False) and self._allowed(src, user, prefs.get(uid)))
                    )
                )
                res[f["key"]] = getattr(user, src, None) if ok else None
            out[it.id] = res
        self._cache[ck] = out
        return out

    @staticmethod
    def _to_uuid(raw: Any) -> uuid.UUID | None:
        """@brief Parse a stored user id; None when absent/invalid."""
        try:
            return uuid.UUID(str(raw)) if raw else None
        except ValueError:
            return None
