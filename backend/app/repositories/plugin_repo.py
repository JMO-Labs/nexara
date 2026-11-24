"""
@file plugin_repo.py
@brief Repository for plugin installs, per-community enablement, tokens and prefs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.plugin import PluginCommunity, PluginInstall, PluginToken, PluginUserPref
from app.models.post import Comment, Post, Reaction
from app.repositories.base import BaseRepository

REMOVED_COMMENT = "This comment was removed."


class PluginRepository(BaseRepository[PluginInstall]):
    """@brief Plugin persistence. Tokens are compared by sha256 hex hash only."""

    model = PluginInstall

    async def get_install(self, plugin_id: str) -> PluginInstall | None:
        """@brief Fetch an install by manifest plugin id."""
        res = await self._session.execute(
            select(PluginInstall).where(PluginInstall.plugin_id == plugin_id)
        )
        return res.scalar_one_or_none()

    async def list_installs(self) -> list[PluginInstall]:
        """@brief List all installs ordered by plugin id."""
        res = await self._session.execute(select(PluginInstall).order_by(PluginInstall.plugin_id))
        return list(res.scalars().all())

    async def create_install(self, **fields: Any) -> PluginInstall:
        """@brief Create an install from model column values."""
        inst = PluginInstall(**fields)
        self._session.add(inst)
        await self._session.flush()
        await self._session.refresh(inst)
        return inst

    async def delete_install(self, install_id: uuid.UUID) -> None:
        """@brief Delete an install (cascades communities, tokens, prefs)."""
        await self._session.execute(delete(PluginInstall).where(PluginInstall.id == install_id))
        await self._session.flush()

    async def get_community(
        self, install_id: uuid.UUID, community_id: uuid.UUID
    ) -> PluginCommunity | None:
        """@brief Fetch per-community enablement row."""
        res = await self._session.execute(
            select(PluginCommunity).where(
                PluginCommunity.install_id == install_id,
                PluginCommunity.community_id == community_id,
            )
        )
        return res.scalar_one_or_none()

    async def upsert_community(self, pc: PluginCommunity) -> PluginCommunity:
        """@brief Insert or update a per-community row (merged by primary key)."""
        merged = await self._session.merge(pc)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def list_enabled_for_event(
        self, community_id: uuid.UUID, event: str
    ) -> list[tuple[PluginInstall, PluginCommunity]]:
        """@brief Running installs enabled in the community and subscribed to event."""
        stmt = (
            select(PluginInstall, PluginCommunity)
            .join(PluginCommunity, PluginCommunity.install_id == PluginInstall.id)
            .where(
                PluginCommunity.community_id == community_id,
                PluginCommunity.enabled.is_(True),
                PluginInstall.status == "running",
                PluginInstall.manifest["events"].contains([event]),
            )
            .order_by(PluginInstall.plugin_id)
        )
        res = await self._session.execute(stmt)
        return [(i, c) for i, c in res.all()]

    async def add_token(
        self, install_id: uuid.UUID, community_id: uuid.UUID, token_hash: str
    ) -> PluginToken:
        """@brief Store a token hash."""
        tok = PluginToken(install_id=install_id, community_id=community_id, token_hash=token_hash)
        self._session.add(tok)
        await self._session.flush()
        await self._session.refresh(tok)
        return tok

    async def revoke_tokens(self, install_id: uuid.UUID, community_id: uuid.UUID | None) -> None:
        """@brief Revoke active tokens for an install (one community, or all if None)."""
        stmt = (
            update(PluginToken)
            .where(PluginToken.install_id == install_id, PluginToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        if community_id is not None:
            stmt = stmt.where(PluginToken.community_id == community_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def resolve_token(
        self, token_hash: str
    ) -> tuple[PluginToken, PluginInstall, PluginCommunity] | None:
        """@brief Resolve a hash to an active token, running install, enabled community."""
        stmt = (
            select(PluginToken, PluginInstall, PluginCommunity)
            .join(PluginInstall, PluginInstall.id == PluginToken.install_id)
            .join(
                PluginCommunity,
                (PluginCommunity.install_id == PluginToken.install_id)
                & (PluginCommunity.community_id == PluginToken.community_id),
            )
            .where(
                PluginToken.token_hash == token_hash,
                PluginToken.revoked_at.is_(None),
                PluginInstall.status == "running",
                PluginCommunity.enabled.is_(True),
            )
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1], row[2]) if row else None

    async def get_user_pref(
        self, install_id: uuid.UUID, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> dict[str, Any]:
        """@brief Per-user pref values in a community; empty dict if none."""
        res = await self._session.execute(
            select(PluginUserPref.values).where(
                PluginUserPref.install_id == install_id,
                PluginUserPref.user_id == user_id,
                PluginUserPref.community_id == community_id,
            )
        )
        return dict(res.scalar_one_or_none() or {})

    async def set_user_pref(
        self,
        install_id: uuid.UUID,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
        values: dict[str, Any],
    ) -> None:
        """@brief Upsert per-user pref values."""
        stmt = pg_insert(PluginUserPref).values(
            install_id=install_id, user_id=user_id, community_id=community_id, values=values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["install_id", "user_id", "community_id"],
            set_={"values": values},
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def soft_delete_bot_content(self, bot_user_id: uuid.UUID) -> int:
        """
        @brief Hide a bot's content in all communities.

        Posts are soft-deleted; comments are tombstoned (row and human replies
        kept, content replaced); reactions are deleted.
        @return Total rows affected.
        """
        now = datetime.now(UTC)
        posts = await self._session.execute(
            update(Post)
            .where(Post.author_id == bot_user_id, Post.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        comments = await self._session.execute(
            update(Comment)
            .where(Comment.author_id == bot_user_id, Comment.content != REMOVED_COMMENT)
            .values(content=REMOVED_COMMENT)
        )
        reactions = await self._session.execute(
            delete(Reaction).where(Reaction.user_id == bot_user_id)
        )
        await self._session.flush()
        return sum(int(getattr(r, "rowcount", 0) or 0) for r in (posts, comments, reactions))

    async def list_communities(self, install_id: uuid.UUID) -> list[PluginCommunity]:
        """@brief All per-community rows of an install."""
        res = await self._session.execute(
            select(PluginCommunity).where(PluginCommunity.install_id == install_id)
        )
        return list(res.scalars().all())
