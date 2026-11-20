"""
@file people_directory_service.py
@brief PeopleDirectoryService: searchable, paged, privacy-filtered people directory.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from app.core.exceptions import ValidationError
from app.models.user import User
from app.repositories.home_people_repo import PersonRow
from app.repositories.people_directory_repo import PeopleDirectoryRepository
from app.schemas.home_people import SharedGroup
from app.schemas.people_directory import DirectoryPerson, DirectoryResponse
from app.services.realtime import presence


class PeopleDirectoryService:
    """
    @brief Builds directory pages for a viewer.

    @param repo PeopleDirectoryRepository.
    @param community_id Community scope.
    @param online_fn Async callable returning online user id strings.
    """

    def __init__(
        self,
        repo: PeopleDirectoryRepository,
        community_id: uuid.UUID,
        online_fn: Callable[[], Awaitable[list[str]]] = presence.get_online_users,
    ) -> None:
        self._repo = repo
        self._community_id = community_id
        self._online_fn = online_fn

    async def list(
        self, viewer: User, *, q: str | None, filter: str, limit: int, cursor: str | None
    ) -> DirectoryResponse:
        """
        @brief Return one page of people.
        @param viewer Viewing user.
        @param q Optional search text.
        @param filter One of ``all``, ``online``, ``groups``.
        @param limit Page size.
        @param cursor Opaque cursor from a previous page (integer offset).
        @return DirectoryResponse with ``next_cursor`` when more rows exist.
        """
        offset = self._offset(cursor)
        online_all = await self._online_fn()
        rows = await self._repo.page(
            viewer.id,
            self._community_id,
            viewer_is_admin=viewer.role == "admin",
            q=q.strip() if q and q.strip() else None,
            online_ids=list(online_all) if filter == "online" else None,
            groups_only=filter == "groups",
            offset=offset,
            limit=limit + 1,
        )
        online_ids = set(online_all)
        items = [self._build(r, online_ids) for r in rows[:limit]]
        more = len(rows) > limit
        return DirectoryResponse(items=items, next_cursor=str(offset + limit) if more else None)

    @staticmethod
    def _offset(cursor: str | None) -> int:
        """@brief Parse the integer-offset cursor or raise a 422."""
        if cursor is None:
            return 0
        try:
            value = int(cursor)
        except ValueError:
            value = -1
        if value < 0:
            raise ValidationError("Invalid cursor")
        return value

    @staticmethod
    def _build(row: PersonRow, online_ids: set[str]) -> DirectoryPerson:
        u = row.user
        primary = min(row.shared_groups, key=lambda g: (g[3], g[1]), default=None)
        return DirectoryPerson(
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            online=row.show_online_status and str(u.id) in online_ids,
            last_seen_at=u.last_seen_at if row.show_last_seen else None,
            shared_groups=[
                SharedGroup(id=g[0], name=g[1], accent_color=g[2]) for g in row.shared_groups
            ],
            primary_group_id=primary[0] if primary else None,
        )
