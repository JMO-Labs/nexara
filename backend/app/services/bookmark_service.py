"""
@file bookmark_service.py
@brief Business logic for post bookmarks.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.repositories.bookmark_repo import BookmarkRepository
from app.repositories.post_repo import PostRepository


class BookmarkService:
    """@brief Toggle, list and delete bookmarks."""

    def __init__(
        self, repo: BookmarkRepository, post_repo: PostRepository, community_id: uuid.UUID
    ) -> None:
        self._repo = repo
        self._posts = post_repo
        self._community_id = community_id

    async def toggle(self, post_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        """
        @brief Create the bookmark if missing, otherwise remove it.
        @return {post_id, is_bookmarked, created_at}.
        @raises NotFoundError If the post does not exist.
        """
        if await self._posts.get_post_detail(post_id, self._community_id, user_id) is None:
            raise NotFoundError(_("Post not found"))
        existing = await self._repo.get_for_user_post(user_id, post_id, self._community_id)
        if existing is not None:
            await self._repo.delete_bookmark(existing)
            return {"post_id": post_id, "is_bookmarked": False, "created_at": None}
        created = await self._repo.create_bookmark(user_id, post_id, self._community_id)
        return {"post_id": post_id, "is_bookmarked": True, "created_at": created.created_at}

    async def list(self, user_id: uuid.UUID, cursor: str | None, limit: int) -> dict[str, Any]:
        """@brief The user's bookmarks, newest first."""
        rows, next_cursor = await self._repo.list_for_user(
            user_id, self._community_id, cursor=cursor, limit=limit
        )
        return {
            "bookmarks": [
                {"id": b.id, "post": post, "bookmarked_at": b.created_at} for b, post in rows
            ],
            "pagination": {"cursor": next_cursor, "has_more": next_cursor is not None},
        }

    async def delete(self, bookmark_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        @brief Delete a bookmark by id (owner only).
        @raises NotFoundError / AuthorizationError.
        """
        bookmark = await self._repo.get_by_id(bookmark_id, self._community_id)
        if bookmark is None:
            raise NotFoundError(_("Bookmark not found"))
        if bookmark.user_id != user_id:
            raise AuthorizationError(_("Not your bookmark"))
        await self._repo.delete_bookmark(bookmark)
