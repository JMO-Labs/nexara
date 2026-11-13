"""
@file kudos_service.py
@brief Business logic for kudos (shoutouts to a recipient).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.post import Post
from app.models.user import User
from app.repositories.kudos_repo import KudosRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.repositories.user_repo import UserRepository
from app.schemas.kudos import KudosCreate, KudosRecipient, KudosResponse
from app.services.notification_service import NotificationService


def _to_response(post: Post, recipient: User | None = None) -> KudosResponse:
    """@brief Map a kudos Post (and optional recipient) to the response schema."""
    return KudosResponse(
        id=post.id,
        recipient_id=post.recipient_id,
        message=post.content or None,
        author_id=post.author_id,
        subgroup_id=post.subgroup_id,
        created_at=post.created_at,
        recipient=KudosRecipient.model_validate(recipient) if recipient else None,
    )


class KudosService:
    """@brief Create, list and delete kudos."""

    def __init__(
        self,
        kudos_repo: KudosRepository,
        user_repo: UserRepository,
        subgroup_repo: SubgroupRepository,
        notification_service: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = kudos_repo
        self._users = user_repo
        self._subgroups = subgroup_repo
        self._notify = notification_service
        self._community_id = community_id

    async def create(self, author: User, body: KudosCreate) -> KudosResponse:
        """
        @brief Create a kudos and notify the recipient.
        @raises AppError 400 on self-kudos.
        @raises NotFoundError If the recipient does not exist.
        @raises AuthorizationError If author is not in the given subgroup.
        """
        if body.recipient_id == author.id:
            raise AppError("SELF_KUDOS", _("You cannot give kudos to yourself"), 400)
        recipient = await self._users.get_by_id(body.recipient_id, self._community_id)
        if recipient is None:
            raise NotFoundError(_("Recipient not found"))
        if body.subgroup_id:
            if not await self._subgroups.is_member(body.subgroup_id, author.id):
                raise AuthorizationError(_("You are not a member of this subgroup"))
            if not await self._subgroups.is_member(body.subgroup_id, recipient.id):
                raise AuthorizationError(_("Recipient is not a member of this subgroup"))
        post = await self._repo.create_kudos(
            author.id, body.recipient_id, body.message or "", self._community_id, body.subgroup_id
        )
        await self._notify.notify(
            body.recipient_id,
            "kudos_received",
            {"message": _("You received kudos"), "link": f"/app/posts/{post.id}"},
            author.id,
        )
        return _to_response(post, recipient)

    async def _list(
        self, viewer_id: uuid.UUID, recipient_id: uuid.UUID | None, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        rows, next_cursor = await self._repo.list_kudos(
            self._community_id, viewer_id, recipient_id=recipient_id, cursor=cursor, limit=limit
        )
        return {
            "kudos": [_to_response(p, r) for p, r in rows],
            "pagination": {"cursor": next_cursor, "has_more": next_cursor is not None},
        }

    async def list_recent(
        self, viewer_id: uuid.UUID, cursor: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
        """@brief Recent kudos visible to the viewer."""
        return await self._list(viewer_id, None, cursor, limit)

    async def list_received(
        self, user_id: uuid.UUID, viewer_id: uuid.UUID, cursor: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
        """@brief Kudos received by ``user_id`` visible to the viewer."""
        return await self._list(viewer_id, user_id, cursor, limit)

    async def delete(self, kudos_id: uuid.UUID, user: User) -> None:
        """
        @brief Soft-delete a kudos (author only).
        @raises NotFoundError / AuthorizationError.
        """
        post = await self._repo.get_by_id(kudos_id, self._community_id)
        if post is None or post.recipient_id is None:
            raise NotFoundError(_("Kudos not found"))
        if post.author_id != user.id:
            raise AuthorizationError(_("Only the author can delete this kudos"))
        await self._repo.soft_delete(post)
