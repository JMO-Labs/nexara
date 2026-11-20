"""
@file home_needs_service.py
@brief HomeNeedsService: aggregates items that need the viewer's attention.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.user import User
from app.repositories.home_needs_repo import HomeNeedsRepository
from app.repositories.subgroup_member_repo import SubgroupMemberRepository
from app.schemas.home_needs import (
    HomeNeedsResponse,
    NeedListItems,
    NeedPoll,
    NeedPrompt,
    NeedRsvp,
)


class HomeNeedsService:
    """
    @brief Builds the "needs you" response for the home page.
    @param repo HomeNeedsRepository.
    @param member_repo SubgroupMemberRepository (viewer memberships).
    @param community_id Community scope.
    """

    def __init__(
        self,
        repo: HomeNeedsRepository,
        member_repo: SubgroupMemberRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._members = member_repo
        self._community_id = community_id

    async def get(self, viewer: User) -> HomeNeedsResponse:
        """
        @brief Collect pending RSVPs, open polls, unanswered prompt and due list items.
        @param viewer Current user.
        @return HomeNeedsResponse (empty collections / None when nothing is pending).
        """
        now = datetime.now(UTC)
        cid = self._community_id
        subgroup_ids = list((await self._members.list_my_roles(viewer.id)).keys())
        rsvps = await self._repo.pending_rsvps(viewer.id, cid, subgroup_ids, now)
        polls = await self._repo.open_polls(viewer.id, cid, subgroup_ids, now)
        prompt = await self._repo.unanswered_prompt(viewer.id, cid, now)
        count, list_id, list_title = await self._repo.due_list_items(
            viewer.id, cid, subgroup_ids, now
        )
        return HomeNeedsResponse(
            rsvps=[NeedRsvp(event_id=e.id, title=e.title, starts_at=e.starts_at) for e in rsvps],
            polls=[NeedPoll(post_id=p.post_id, question=p.question) for p in polls if p.post_id],
            prompt=(
                NeedPrompt(prompt_post_id=prompt[0], post_id=prompt[1], title=prompt[2])
                if prompt
                else None
            ),
            list_items=(
                NeedListItems(count=count, list_id=list_id, list_title=list_title or "")
                if count and list_id
                else None
            ),
        )
