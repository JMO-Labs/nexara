"""
@file list_activity_service.py
@brief Records and reads the append-only per-list activity log.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.list_assignment import ListActivity
from app.models.user import User
from app.repositories.list_activity_repo import ListActivityRepository
from app.repositories.list_repo import ListRepository

ACTIONS = (
    "item_added",
    "item_edited",
    "item_removed",
    "completed",
    "uncompleted",
    "taken",
    "assigned",
    "accepted",
    "declined",
    "released",
    "unassigned",
    "signup_claimed",
    "signup_released",
    "missed",
)


class ListActivityService:
    """@brief Append activity entries; page them newest-first for viewers."""

    def __init__(
        self, repo: ListActivityRepository, repo_list: ListRepository, community_id: uuid.UUID
    ) -> None:
        """
        @param repo Activity repository.
        @param repo_list List repository (view check).
        @param community_id Tenant scope.
        """
        self._repo = repo
        self._lists = repo_list
        self._community_id = community_id

    async def record(
        self,
        list_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: str,
        item_id: uuid.UUID | None = None,
        item_title: str = "",
        target_user_id: uuid.UUID | None = None,
    ) -> ListActivity:
        """
        @brief Append one entry (title is a snapshot, kept after item deletion).

        @param action One of ``ACTIONS``.
        """
        return await self._repo.add(
            self._community_id, list_id, actor_id, action, item_id, item_title, target_user_id
        )

    async def users(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
        """@brief Users for display hydration."""
        return await self._repo.users_by_ids(self._community_id, ids)

    async def page(
        self, list_id: uuid.UUID, viewer_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[ListActivity], dict[uuid.UUID, User], str | None]:
        """
        @brief Newest-first page for a viewer of the list.

        @return (entries, users by id, next_cursor).
        @raises NotFoundError When the list is missing or hidden.
        """
        lst = await self._lists.get_by_id(list_id, self._community_id)
        if lst is None or not await self._lists.can_view(lst, viewer_id):
            raise NotFoundError(_("List not found"))
        rows, nxt = await self._repo.list_page(self._community_id, list_id, cursor, limit)
        ids = {r.actor_id for r in rows if r.actor_id} | {
            r.target_user_id for r in rows if r.target_user_id
        }
        return rows, await self.users(ids), nxt
