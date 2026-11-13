"""
@file test_prompt_summary_media.py
@brief Unit tests for media attachment on prompt summary posts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.post import Post
from app.models.prompt import PromptPost
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.services.prompt_service import PromptService

from .test_prompt_service import COMMUNITY_ID, _make_prompt


@pytest.fixture
def prompt_repo() -> AsyncMock:
    return AsyncMock(spec=PromptRepository)


@pytest.fixture
def post_repo() -> AsyncMock:
    return AsyncMock(spec=PostRepository)


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


class TestSummaryMediaAttach:
    async def _run(
        self,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
        session: AsyncMock,
        replies: list[dict],
        scope: str = "community",
        subgroup_id: uuid.UUID | None = None,
    ) -> tuple[AsyncMock, uuid.UUID]:
        attacher = AsyncMock()
        svc = PromptService(
            prompt_repo=prompt_repo,
            post_repo=post_repo,
            community_id=COMMUNITY_ID,
            session=session,
            media_attacher=attacher,
        )
        prompt = _make_prompt()
        prompt.scope = scope
        prompt.subgroup_id = subgroup_id
        tracker = MagicMock(spec=PromptPost)
        tracker.prompt_id = prompt.id
        tracker.post_id = uuid.uuid4()
        tracker.response_count = len(replies)
        prompt_repo.list_expired_unfinalised.return_value = [tracker]
        prompt_repo.get_by_id.return_value = prompt
        post_repo.list_replies_for_prompt.return_value = replies
        post_repo.get_by_id.return_value = MagicMock(spec=Post)
        summary_id = uuid.uuid4()

        def _fill(p: Post) -> Post:
            p.id = summary_id
            return p

        post_repo.create.side_effect = _fill
        await svc.finalise_expired(datetime.now(UTC))
        return attacher, summary_id

    @pytest.mark.asyncio
    async def test_attaches_both_media_in_order(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        m1, m2 = uuid.uuid4(), uuid.uuid4()
        replies = [
            {"id": uuid.uuid4(), "media_ids": [m1], "visibility": "community"},
            {"id": uuid.uuid4(), "media_ids": [m2], "visibility": "community"},
        ]
        attacher, sid = await self._run(prompt_repo, post_repo, session, replies)
        attacher.assert_awaited_once_with(sid, [m1, m2])

    @pytest.mark.asyncio
    async def test_dedupes_preserving_order(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        m1, m2 = uuid.uuid4(), uuid.uuid4()
        replies = [
            {"id": uuid.uuid4(), "media_ids": [m1, m2], "visibility": "community"},
            {"id": uuid.uuid4(), "media_ids": [m1], "visibility": "community"},
        ]
        attacher, sid = await self._run(prompt_repo, post_repo, session, replies)
        attacher.assert_awaited_once_with(sid, [m1, m2])

    @pytest.mark.asyncio
    async def test_caps_at_post_media_limit(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        from app.services.media_service import MAX_POST_MEDIA

        ids = [uuid.uuid4() for _ in range(MAX_POST_MEDIA + 3)]
        replies = [{"id": uuid.uuid4(), "media_ids": ids, "visibility": "community"}]
        attacher, sid = await self._run(prompt_repo, post_repo, session, replies)
        attacher.assert_awaited_once_with(sid, ids[:MAX_POST_MEDIA])

    @pytest.mark.asyncio
    async def test_excludes_private_and_other_subgroup_media(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        pub, priv, sub = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        replies = [
            {"id": uuid.uuid4(), "media_ids": [pub], "visibility": "community"},
            {"id": uuid.uuid4(), "media_ids": [priv], "visibility": "private"},
            {
                "id": uuid.uuid4(),
                "media_ids": [sub],
                "visibility": "subgroup",
                "subgroup_id": uuid.uuid4(),
            },
        ]
        attacher, sid = await self._run(prompt_repo, post_repo, session, replies)
        attacher.assert_awaited_once_with(sid, [pub])

    @pytest.mark.asyncio
    async def test_subgroup_prompt_summary_is_subgroup_scoped(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        sg, other = uuid.uuid4(), uuid.uuid4()
        mine, theirs, priv = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        replies = [
            {"id": uuid.uuid4(), "media_ids": [mine], "visibility": "subgroup", "subgroup_id": sg},
            {
                "id": uuid.uuid4(),
                "media_ids": [theirs],
                "visibility": "subgroup",
                "subgroup_id": other,
            },
            {"id": uuid.uuid4(), "media_ids": [priv], "visibility": "private"},
        ]
        attacher, sid = await self._run(
            prompt_repo, post_repo, session, replies, scope="subgroup", subgroup_id=sg
        )
        attacher.assert_awaited_once_with(sid, [mine])
        created = post_repo.create.call_args.args[0]
        assert created.visibility == "subgroup"
        assert created.subgroup_id == sg

    @pytest.mark.asyncio
    async def test_no_media_skips_attacher(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        attacher, _sid = await self._run(
            prompt_repo,
            post_repo,
            session,
            [{"id": uuid.uuid4(), "media_ids": [], "visibility": "community"}],
        )
        attacher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_visibility_is_excluded(
        self, prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock
    ) -> None:
        replies = [{"id": uuid.uuid4(), "media_ids": [uuid.uuid4()]}]
        attacher, _sid = await self._run(prompt_repo, post_repo, session, replies)
        attacher.assert_not_awaited()
