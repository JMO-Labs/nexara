"""
@file test_nsfw_gating_more.py
@brief Real Postgres, teen vs adult: NSFW photos inside safe posts, prompt
       summary media, kudos/mention notifications, reports, recap daily
       question, home "needs you" polls and poll endpoints.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.poll import Poll
from app.models.post import Post
from app.models.prompt import PromptPost
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.home_needs_repo import HomeNeedsRepository
from app.repositories.kudos_repo import KudosRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.poll_repo import PollRepository
from app.repositories.post_enrichment import enrich_posts
from app.repositories.post_repo import PostRepository
from app.repositories.recap_repo import RecapRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.repositories.user_repo import UserRepository
from app.schemas.kudos import KudosCreate
from app.services.kudos_service import KudosService
from app.services.moderation_service import ModerationService
from app.services.notification_service import NotificationService
from app.services.poll_service import PollService
from app.services.post_service import PostService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    attach,
    make_album,
    make_media,
    make_post,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
)
from tests.integration.repositories.test_answer_reveal import _prompt_post


def _notif(s: AsyncSession) -> NotificationService:
    return NotificationService(
        NotificationRepository(s), SettingsRepository(s), CID, dispatcher=AsyncMock()
    )


async def _inbox(s: AsyncSession, user_id) -> list[Notification]:
    return (await _notif(s).list_for_user(user_id)).items  # type: ignore[return-value]


async def _stored(s: AsyncSession, user_id) -> int:
    stmt = select(Notification).where(Notification.user_id == user_id)
    return len((await s.execute(stmt)).scalars().all())


class TestPhotosInSafePosts:
    async def test_flagged_photo_dropped_for_teen_marked_for_adult(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        p = await make_post(session, owner, nsfw=False)
        safe, flagged = (
            await make_media(session, owner),
            await make_media(session, owner, nsfw=True),
        )
        in_album = await make_media(session, owner)
        await make_album(session, owner, nsfw=True, media=in_album)
        for m in (safe, flagged, in_album):
            await attach(session, p, m)
        kid_media = (await enrich_posts(session, [p.id], kid.id))[p.id]["media"]
        assert [x["id"] for x in kid_media] == [str(safe.id)]
        adult_media = {
            x["id"]: x["is_nsfw"]
            for x in (await enrich_posts(session, [p.id], grown.id))[p.id]["media"]
        }
        assert adult_media == {str(safe.id): False, str(flagged.id): True, str(in_album.id): True}

    async def test_prompt_summary_skips_flagged_photos(self, session) -> None:
        owner = await adult(session)
        pp_id = await _prompt_post(session, owner, False)
        reply = await make_post(session, owner, nsfw=False, reply_to_prompt_id=pp_id)
        safe, flagged = (
            await make_media(session, owner),
            await make_media(session, owner, nsfw=True),
        )
        await attach(session, reply, safe)
        await attach(session, reply, flagged)
        rows = await PostRepository(session).list_replies_for_prompt(pp_id)
        assert rows[0]["media_ids"] == [safe.id]


class TestNotifications:
    async def test_kudos_notification_hidden_once_flagged(self, session) -> None:
        giver, kid = await adult(session), await teen(session)
        svc = KudosService(
            KudosRepository(session),
            UserRepository(session),
            SubgroupRepository(session),
            _notif(session),
            CID,
        )
        out = await svc.create(giver, KudosCreate(recipient_id=kid.id, message="well done"))
        assert len(await _inbox(session, kid.id)) == 1
        post = await session.get(Post, out.id)
        post.is_nsfw = True
        await session.flush()
        assert await _inbox(session, kid.id) == []

    async def test_mention_on_nsfw_post_reaches_adults_only(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        svc = PostService(
            PostRepository(session),
            CommentRepository(session),
            ReactionRepository(session),
            _notif(session),
            CID,
        )
        await svc.create_post(author, f"hi @{grown.username} @{kid.username}", is_nsfw=True)
        assert await _stored(session, grown.id) == 1
        assert await _stored(session, kid.id) == 0


class TestReport:
    async def test_teen_report_on_nsfw_post_is_404(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        p = await make_post(session, author, nsfw=True)
        svc = ModerationService(ModerationRepository(session), AsyncMock(), CID)
        with pytest.raises(NotFoundError):
            await svc.create_report(kid.id, "post", p.id, "spam", None)
        assert (await svc.create_report(grown.id, "post", p.id, "spam", None)).id


class TestRecapHomePolls:
    async def test_recap_daily_question(self, session) -> None:
        admin, grown, kid = await adult(session), await adult(session), await teen(session)
        pp_id = await _prompt_post(session, admin, True)
        pp = await session.get(PromptPost, pp_id)
        host = await session.get(Post, pp.post_id)
        host.is_nsfw = True
        await session.flush()
        repo = RecapRepository(session)
        assert await repo.yesterday_daily(CID, date.today(), kid.id) is None
        assert (await repo.yesterday_daily(CID, date.today(), grown.id))[0] == host.id

    async def _poll(self, s: AsyncSession, author) -> Poll:
        p = await make_post(s, author, nsfw=True)
        poll = Poll(community_id=CID, post_id=p.id, created_by=author.id, question="Q?")
        s.add(poll)
        await s.flush()
        return poll

    async def test_home_needs_polls(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        poll = await self._poll(session, author)
        repo = HomeNeedsRepository(session)
        now = datetime.now(UTC)
        assert poll.id not in {p.id for p in await repo.open_polls(kid.id, CID, [], now, 50)}
        assert poll.id in {p.id for p in await repo.open_polls(grown.id, CID, [], now, 50)}

    async def test_poll_endpoints(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        poll = await self._poll(session, author)
        svc = PollService(PollRepository(session), CID)
        with pytest.raises(NotFoundError):
            await svc.get_poll(poll.id, kid.id)
        with pytest.raises(NotFoundError):
            await svc.get_results(poll.id, kid.id)
        with pytest.raises(NotFoundError):
            await svc.cast_vote(poll.id, kid.id, [])
        assert (await svc.get_poll(poll.id, grown.id)).id == poll.id
