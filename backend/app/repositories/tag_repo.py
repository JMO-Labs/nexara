"""
@file tag_repo.py
@brief Tags: sync from @mentions, add/remove on photos, per-target lists and
       a person's "Tagged" feed filtered by what the viewer may see.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.post import Comment, Post
from app.models.subgroup import SubgroupMember
from app.models.tag import Tag
from app.models.user import User
from app.repositories.household_repo import household_visible
from app.repositories.visibility_preds import (
    media_nsfw_ok,
    media_visible,
    my_subgroup_ids,
    not_blocked,
    post_visible,
)


class TagRepository:
    """@brief Data access for the tags table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- writes -------------------------------------------------------------

    async def replace_user_tags(
        self,
        community_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        tagged_by: uuid.UUID,
        subject_type: str = "user",
    ) -> list[uuid.UUID]:
        """
        @brief Make the target's tags of ``subject_type`` exactly ``user_ids``.
        @return ids that were newly tagged (callers notify these only).
        """
        current = set(
            (
                await self._session.execute(
                    select(Tag.subject_id).where(
                        Tag.target_type == target_type,
                        Tag.target_id == target_id,
                        Tag.subject_type == subject_type,
                    )
                )
            ).scalars()
        )
        wanted = set(user_ids)
        if current - wanted:
            await self._session.execute(
                delete(Tag).where(
                    Tag.target_type == target_type,
                    Tag.target_id == target_id,
                    Tag.subject_type == subject_type,
                    Tag.subject_id.in_(current - wanted),
                )
            )
        new = [u for u in user_ids if u not in current]
        for uid in new:
            await self.add(community_id, target_type, target_id, uid, tagged_by, subject_type)
        return new

    async def add(
        self,
        community_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        user_id: uuid.UUID,
        tagged_by: uuid.UUID,
        subject_type: str = "user",
    ) -> bool:
        """@brief Insert one tag (user or household); False when it already existed."""
        stmt = (
            insert(Tag)
            .values(
                community_id=community_id,
                target_type=target_type,
                target_id=target_id,
                subject_type=subject_type,
                subject_id=user_id,
                tagged_by=tagged_by,
            )
            .on_conflict_do_nothing(constraint="tags_unique")
            .returning(Tag.id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def get(self, tag_id: uuid.UUID, community_id: uuid.UUID) -> Tag | None:
        """@brief One tag in the community."""
        stmt = select(Tag).where(Tag.id == tag_id, Tag.community_id == community_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def remove(self, tag: Tag) -> None:
        """@brief Delete a tag."""
        await self._session.delete(tag)
        await self._session.flush()

    # -- reads --------------------------------------------------------------

    async def list_for_target(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Tags on one target with the tagged person's name/avatar."""
        stmt = (
            select(
                Tag.id, Tag.tagged_by, User.id, User.username, User.display_name, User.avatar_url
            )
            .join(User, User.id == Tag.subject_id)
            .where(
                Tag.community_id == community_id,
                Tag.target_type == target_type,
                Tag.target_id == target_id,
                Tag.subject_type == "user",
                User.deleted_at.is_(None),
            )
            .order_by(Tag.created_at)
        )
        return [
            {
                "id": tid,
                "tagged_by": by,
                "user": {"id": uid, "username": un, "display_name": dn, "avatar_url": av},
            }
            for tid, by, uid, un, dn, av in (await self._session.execute(stmt)).all()
        ]

    async def household_for_target(
        self, target_type: str, target_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """@brief Household members/pets tagged on a target that the viewer may see."""
        stmt = (
            select(
                Tag.id,
                Tag.tagged_by,
                HouseholdMember.id,
                HouseholdMember.name,
                HouseholdMember.kind,
                HouseholdMember.photo_media_id,
            )
            .join(HouseholdMember, HouseholdMember.id == Tag.subject_id)
            .where(
                Tag.community_id == community_id,
                Tag.target_type == target_type,
                Tag.target_id == target_id,
                Tag.subject_type == "household",
                household_visible(viewer_id, community_id),
            )
            .order_by(Tag.created_at)
        )
        return [
            {
                "id": tid,
                "tagged_by": by,
                "household": {"id": hid, "name": n, "kind": k, "photo_media_id": ph},
            }
            for tid, by, hid, n, k, ph in (await self._session.execute(stmt)).all()
        ]

    async def household_owner(self, member_id: uuid.UUID, community_id: uuid.UUID) -> Any:
        """@brief Owner id of a household member, or None."""
        stmt = select(HouseholdMember.owner_id).where(
            HouseholdMember.id == member_id, HouseholdMember.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def household_viewable(
        self, member_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Viewer may see this household member."""
        stmt = select(
            exists().where(
                HouseholdMember.id == member_id, household_visible(viewer_id, community_id)
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def users_by_username(self, community_id: uuid.UUID, usernames: list[str]) -> list[User]:
        """@brief Active users with these usernames in the community."""
        if not usernames:
            return []
        stmt = select(User).where(
            User.community_id == community_id,
            User.username.in_(usernames),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.memorialized_at.is_(None),
        )
        return list((await self._session.execute(stmt)).scalars())

    async def users_by_ids(self, community_id: uuid.UUID, ids: list[uuid.UUID]) -> list[User]:
        """@brief Active users by id in the community."""
        stmt = select(User).where(
            User.community_id == community_id,
            User.id.in_(ids),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.memorialized_at.is_(None),
        )
        return list((await self._session.execute(stmt)).scalars())

    async def subgroup_member_ids(
        self, subgroup_id: uuid.UUID, user_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """@brief Which of ``user_ids`` belong to the subgroup."""
        if not user_ids:
            return set()
        stmt = select(SubgroupMember.user_id).where(
            SubgroupMember.subgroup_id == subgroup_id, SubgroupMember.user_id.in_(user_ids)
        )
        return set((await self._session.execute(stmt)).scalars())

    async def blocked_with(self, user_id: uuid.UUID, others: list[uuid.UUID]) -> set[uuid.UUID]:
        """@brief Which of ``others`` are in a block relation with ``user_id``."""
        if not others:
            return set()
        stmt = select(UserBlock.blocker_id, UserBlock.blocked_id).where(
            or_(
                and_(UserBlock.blocker_id == user_id, UserBlock.blocked_id.in_(others)),
                and_(UserBlock.blocked_id == user_id, UserBlock.blocker_id.in_(others)),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return {b if a == user_id else a for a, b in rows}

    async def media_viewable(
        self, media_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Uploader, or the photo is in a post/gallery the viewer can see."""
        stmt = select(
            exists().where(
                Media.id == media_id,
                Media.community_id == community_id,
                or_(
                    Media.uploader_id == viewer_id,
                    media_visible(Media.id, viewer_id, my_subgroup_ids(viewer_id), community_id),
                ),
                media_nsfw_ok(Media.id, viewer_id),
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def media_uploader(
        self, media_id: uuid.UUID, community_id: uuid.UUID
    ) -> uuid.UUID | None:
        """@brief Uploader of a photo in the community, or None."""
        stmt = select(Media.uploader_id).where(
            Media.id == media_id, Media.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def comment_post_id(
        self, comment_id: uuid.UUID, community_id: uuid.UUID
    ) -> uuid.UUID | None:
        """@brief Post a comment in the community belongs to."""
        stmt = select(Comment.post_id).where(
            Comment.id == comment_id, Comment.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def tagged_post_ids(
        self,
        community_id: uuid.UUID,
        subject_id: uuid.UUID,
        viewer_id: uuid.UUID,
        before: datetime | None,
        limit: int,
        subject_type: str = "user",
    ) -> list[tuple[uuid.UUID, datetime]]:
        """
        @brief Posts the person (or group) is tagged in (directly or in a comment) that the
               viewer can read, newest tag first.
        @return (post_id, tagged_at) pairs.
        """
        on_post = and_(Tag.target_type == "post", Tag.target_id == Post.id)
        on_comment = and_(
            Tag.target_type == "comment",
            exists().where(Comment.id == Tag.target_id, Comment.post_id == Post.id),
        )
        tagged_at = func.max(Tag.created_at).label("tagged_at")
        stmt = (
            select(Post.id, tagged_at)
            .join(Tag, or_(on_post, on_comment))
            .where(
                Tag.community_id == community_id,
                Tag.subject_type == subject_type,
                Tag.subject_id == subject_id,
                post_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
            )
            .group_by(Post.id)
            .order_by(tagged_at.desc(), Post.id.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.having(func.max(Tag.created_at) < before)
        return [(pid, at) for pid, at in (await self._session.execute(stmt)).all()]

    async def tagged_media(
        self,
        community_id: uuid.UUID,
        subject_id: uuid.UUID,
        viewer_id: uuid.UUID,
        before: datetime | None,
        limit: int,
        subject_type: str = "user",
    ) -> list[tuple[uuid.UUID, datetime]]:
        """@brief Photos the person (or household member) is tagged in that the viewer can see."""
        stmt = (
            select(Media.id, Tag.created_at)
            .join(Tag, and_(Tag.target_type == "media", Tag.target_id == Media.id))
            .where(
                Tag.community_id == community_id,
                Media.community_id == community_id,
                Tag.subject_type == subject_type,
                Tag.subject_id == subject_id,
                or_(
                    Media.uploader_id == viewer_id,
                    media_visible(Media.id, viewer_id, my_subgroup_ids(viewer_id), community_id),
                ),
                media_nsfw_ok(Media.id, viewer_id),
                not_blocked(Media.uploader_id, viewer_id),
            )
            .order_by(Tag.created_at.desc(), Media.id.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.where(Tag.created_at < before)
        return [(mid, at) for mid, at in (await self._session.execute(stmt)).all()]

    async def household_by_handles(
        self, community_id: uuid.UUID, viewer_id: uuid.UUID, handles: list[str]
    ) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """@brief (member id, owner id) for handles the viewer may see."""
        if not handles:
            return []
        stmt = select(HouseholdMember.id, HouseholdMember.owner_id).where(
            HouseholdMember.handle.in_([h.lower() for h in handles]),
            household_visible(viewer_id, community_id),
        )
        return [(r[0], r[1]) for r in (await self._session.execute(stmt)).all()]

    async def display_name(self, user_id: uuid.UUID) -> str:
        """@brief A user's display name ('' if missing), for tag notifications."""
        stmt = select(User.display_name).where(User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none() or ""
