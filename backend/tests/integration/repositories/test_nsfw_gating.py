"""
@file test_nsfw_gating.py
@brief Review-focus, real Postgres: NSFW posts never reach a teen (or an
       unknown-age user) through any post read path; adults still see them.
       Media, albums, notifications and activity: test_nsfw_gating_media.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.bookmark import Bookmark
from app.models.community import Community
from app.models.media import Media
from app.models.post import PostMedia
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.tag import Tag
from app.models.user import User
from app.repositories.bookmark_repo import BookmarkRepository
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.newsletter_repo import NewsletterRepository
from app.repositories.post_enrichment import enrich_posts
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.post_repo import PostRepository
from app.repositories.search_repo import SearchRepository
from app.repositories.story_repo import StoryRepository
from app.repositories.tag_repo import TagRepository
from app.services.age_service import is_adult
from app.services.post_service import PostService
from app.services.search_service import SearchService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    ids,
    make_post,
    make_user,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
    years_ago,
)


def _svc(s: AsyncSession, notif: Any | None = None) -> PostService:
    return PostService(
        PostRepository(s),
        CommentRepository(s),
        ReactionRepository(s),
        notif or AsyncMock(),
        CID,
    )


async def _viewers(s: AsyncSession) -> tuple[User, User, User]:
    """@return (adult author, adult viewer, teen viewer)."""
    return await adult(s), await adult(s), await teen(s)


class TestAgeParity:
    """@brief SQL ``viewer_is_adult`` must agree with ``age_service.is_adult``."""

    @pytest.mark.parametrize(
        "birthday_years,group,approval",
        [
            (30, None, False),
            (15, None, False),
            (8, None, False),
            (None, None, False),
            (30, None, True),
            (30, "teen", False),
            (15, "adult", False),
            (None, "adult", True),
            (30, "child", False),
        ],
    )
    async def test_matches_python(self, session, birthday_years, group, approval) -> None:
        community = await session.get(Community, CID)
        community.adult_requires_approval = approval
        await session.flush()
        bday = years_ago(birthday_years) if birthday_years is not None else None
        u = await make_user(session, birthday=bday, age_group=group)
        sql = await PostRepository(session).viewer_adult(u.id)
        assert sql is is_adult(u, community)

    async def test_eighteenth_birthday_today(self, session) -> None:
        community = await session.get(Community, CID)
        community.adult_requires_approval = False
        today = datetime.now(UTC).date()
        if (today.month, today.day) == (2, 29):
            pytest.skip("leap day")
        just18 = await make_user(session, birthday=today.replace(year=today.year - 18))
        not_yet = await make_user(
            session, birthday=(today + timedelta(days=1)).replace(year=today.year - 18)
        )
        repo = PostRepository(session)
        assert await repo.viewer_adult(just18.id) is is_adult(just18, community) is True
        assert await repo.viewer_adult(not_yet.id) is is_adult(not_yet, community) is False


class TestPostDetailAndComments:
    async def test_detail_404_for_teen_ok_for_adult(self, session) -> None:
        author, grown, kid = await _viewers(session)
        p = await make_post(session, author, nsfw=True)
        with pytest.raises(NotFoundError):
            await _svc(session).get_post(p.id, viewer_id=kid.id)
        assert (await _svc(session).get_post(p.id, viewer_id=grown.id))["is_nsfw"] is True

    async def test_comments_list_404_for_teen(self, session) -> None:
        author, grown, kid = await _viewers(session)
        p = await make_post(session, author, nsfw=True)
        with pytest.raises(NotFoundError):
            await _svc(session).list_comments(p.id, kid.id)
        assert (await _svc(session).list_comments(p.id, grown.id))["items"] == []

    async def test_teen_cannot_comment_or_react(self, session) -> None:
        author, _grown, kid = await _viewers(session)
        p = await make_post(session, author, nsfw=True)
        with pytest.raises(NotFoundError):
            await _svc(session).add_comment(p.id, kid, "hi")
        with pytest.raises(NotFoundError):
            await _svc(session).toggle_reaction(p.id, kid, "❤️")

    async def test_teen_cannot_mark_nsfw(self, session) -> None:
        kid = await teen(session)
        with pytest.raises(AuthorizationError):
            await _svc(session).create_post(kid, "x", is_nsfw=True)

    async def test_teen_author_cannot_unflag(self, session) -> None:
        kid = await teen(session)
        p = await make_post(session, kid, nsfw=True)
        with pytest.raises(AuthorizationError):
            await _svc(session).update_post(p.id, kid, "x", is_nsfw=False)


class TestLists:
    async def test_feed_and_count(self, session) -> None:
        author, grown, kid = await _viewers(session)
        bad = await make_post(session, author, nsfw=True)
        ok = await make_post(session, author, nsfw=False)
        repo = PostRepository(session)
        teen_feed, _ = await repo.list_feed(CID, viewer_id=kid.id, limit=50)
        adult_feed, _ = await repo.list_feed(CID, viewer_id=grown.id, limit=50)
        assert str(bad.id) not in ids(teen_feed) and str(ok.id) in ids(teen_feed)
        assert str(bad.id) in ids(adult_feed)
        since = datetime.now(UTC) - timedelta(hours=1)
        assert await repo.count_new_since(CID, kid.id, since) + 1 == await repo.count_new_since(
            CID, grown.id, since
        )

    async def test_group_feed(self, session) -> None:
        author, grown, kid = await _viewers(session)
        sg = Subgroup(community_id=CID, name="G", slug=f"nsfw-{kid.id.hex[:8]}")
        session.add(sg)
        await session.flush()
        for u in (author, grown, kid):
            session.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=u.id))
        await session.flush()
        bad = await make_post(session, author, nsfw=True, subgroup_id=sg.id, visibility="subgroup")
        repo = PostRepository(session)
        teen_feed, _ = await repo.list_feed(CID, viewer_id=kid.id, subgroup_id=sg.id)
        adult_feed, _ = await repo.list_feed(CID, viewer_id=grown.id, subgroup_id=sg.id)
        assert str(bad.id) not in ids(teen_feed)
        assert str(bad.id) in ids(adult_feed)

    async def test_profile_tags_and_stories(self, session) -> None:
        author, grown, kid = await _viewers(session)
        bad = await make_post(session, author, nsfw=True)
        session.add(
            Tag(
                community_id=CID,
                target_type="post",
                target_id=bad.id,
                subject_type="user",
                subject_id=author.id,
                tagged_by=author.id,
            )
        )
        audio = Media(
            community_id=CID,
            uploader_id=author.id,
            filename="a.mp3",
            content_type="audio/mpeg",
            storage_key=f"k/{bad.id}",
            size_bytes=1,
            status="ready",
        )
        session.add(audio)
        await session.flush()
        session.add(PostMedia(post_id=bad.id, media_id=audio.id))
        await session.flush()
        tags = TagRepository(session)
        assert await tags.tagged_post_ids(CID, author.id, kid.id, None, 20) == []
        assert [p for p, _ in await tags.tagged_post_ids(CID, author.id, grown.id, None, 20)] == [
            bad.id
        ]
        stories = StoryRepository(session)
        assert (await stories.stories_of(author.id, kid.id, CID, None, 20))[0] == []
        assert len((await stories.stories_of(author.id, grown.id, CID, None, 20))[0]) == 1

    async def test_search(self, session) -> None:
        author, grown, kid = await _viewers(session)
        word = f"zq{kid.id.hex[:10]}"
        await make_post(session, author, nsfw=True, content=f"secret {word}")
        community = await session.get(Community, CID)
        svc = SearchService(SearchRepository(session), CID, None, community)

        async def hits(u: User) -> int:
            res = await svc.search(word, u, ["posts", "comments"], None, 20)
            return sum(r.total for r in res.results.values())

        assert await hits(kid) == 0
        assert await hits(grown) == 1

    async def test_newsletter(self, session) -> None:
        author, grown, kid = await _viewers(session)
        bad = await make_post(session, author, nsfw=True)
        now = datetime.now(UTC)
        start, end = now - timedelta(days=1), now + timedelta(days=1)
        repo = NewsletterRepository(session, CID)
        rows = await repo.month_posts(kid.id, start, end, now.strftime("%Y-%m"))
        assert bad.id not in {r[0].id for r in rows}

    async def test_on_this_day(self, session) -> None:
        author, grown, kid = await _viewers(session)
        today = datetime.now(UTC)
        if (today.month, today.day) == (2, 29):
            pytest.skip("leap day")
        bad = await make_post(session, author, nsfw=True)
        bad.created_at = today.replace(year=today.year - 1)
        await session.flush()
        repo = PostMemoriesRepository(session)
        args = (today.month, today.day, today.year)
        assert str(bad.id) not in ids(await repo.on_this_day(CID, kid.id, *args))
        assert str(bad.id) in ids(await repo.on_this_day(CID, grown.id, *args))

    async def test_bookmarks_and_enrichment(self, session) -> None:
        author, grown, kid = await _viewers(session)
        bad = await make_post(session, author, nsfw=True)
        session.add(Bookmark(community_id=CID, user_id=kid.id, post_id=bad.id))
        await session.flush()
        rows, _ = await BookmarkRepository(session).list_for_user(kid.id, CID)
        assert rows == []
        assert await enrich_posts(session, [bad.id], kid.id) == {}
        assert await enrich_posts(session, [bad.id], None) == {}
        assert bad.id in await enrich_posts(session, [bad.id], grown.id)

    async def test_prompt_responses(self, session) -> None:
        author, grown, kid = await _viewers(session)
        from tests.integration.repositories.test_answer_reveal import _prompt_post

        pp_id = await _prompt_post(session, author, False)
        bad = await make_post(session, author, nsfw=True, reply_to_prompt_id=pp_id)
        repo = PostRepository(session)
        teen_items, _ = await repo.list_responses(CID, pp_id, viewer_id=kid.id)
        adult_items, _ = await repo.list_responses(CID, pp_id, viewer_id=grown.id)
        assert str(bad.id) not in ids(teen_items)
        assert str(bad.id) in ids(adult_items)
        # prompt summaries are shown to everyone: never built from NSFW answers
        assert await repo.list_replies_for_prompt(pp_id) == []


class TestUnknownAge:
    async def test_no_birthday_is_treated_as_teen(self, session) -> None:
        author = await adult(session)
        unknown = await make_user(session)
        p = await make_post(session, author, nsfw=True)
        with pytest.raises(NotFoundError):
            await _svc(session).get_post(p.id, viewer_id=unknown.id)

    async def test_approval_required_adult_is_treated_as_teen(self, session) -> None:
        author = await make_user(session, age_group="adult")
        community = await session.get(Community, CID)
        community.adult_requires_approval = True
        pending = await adult(session)
        p = await make_post(session, author, nsfw=True)
        with pytest.raises(NotFoundError):
            await _svc(session).get_post(p.id, viewer_id=pending.id)
        feed, _ = await PostRepository(session).list_feed(CID, viewer_id=pending.id, limit=50)
        assert str(p.id) not in ids(feed)
