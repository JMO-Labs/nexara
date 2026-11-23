"""
@file test_answer_reveal.py
@brief Real-Postgres: daily-question answers stay hidden from the feed until
       the viewer answers the same prompt post.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.models.user import User
from app.repositories.visibility_preds import my_subgroup_ids, post_visible

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"rv_{name}_{sfx}@nexara.dev", username=f"rv_{name}_{sfx}",
        display_name=name,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _post(s: AsyncSession, author: User, reply_to: uuid.UUID | None = None) -> Post:
    p = Post(community_id=CID, author_id=author.id, content="a", reply_to_prompt_id=reply_to)
    s.add(p)
    await s.flush()
    return p


async def _visible(s: AsyncSession, viewer: User) -> set[uuid.UUID]:
    stmt = select(Post.id).where(post_visible(viewer.id, my_subgroup_ids(viewer.id), CID))
    return set((await s.execute(stmt)).scalars().all())


async def _prompt_post(s: AsyncSession, admin: User, reveal: bool) -> uuid.UUID:
    prompt = Prompt(
        community_id=CID, title="Q", body="Q?", frequency_type="daily", created_by=admin.id,
        prompt_type="daily_question" if reveal else "standard", reveal_after_answer=reveal,
    )  # fmt: skip
    s.add(prompt)
    await s.flush()
    host = await _post(s, admin)
    pp = PromptPost(
        community_id=CID, prompt_id=prompt.id, post_id=host.id, fired_at=date.today(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )  # fmt: skip
    s.add(pp)
    await s.flush()
    return pp.id


async def test_answers_hidden_until_viewer_answers(session: AsyncSession) -> None:
    admin, ruth, maya = [await _user(session, n) for n in ("admin", "ruth", "maya")]
    pp = await _prompt_post(session, admin, reveal=True)
    ruth_answer = await _post(session, ruth, pp)
    assert ruth_answer.id not in await _visible(session, maya)
    assert ruth_answer.id in await _visible(session, ruth)  # own answer
    assert ruth_answer.id in await _visible(session, admin)  # prompt creator
    await _post(session, maya, pp)
    assert ruth_answer.id in await _visible(session, maya)


async def test_ordinary_prompt_answers_visible(session: AsyncSession) -> None:
    admin, ruth, maya = [await _user(session, n) for n in ("admin", "ruth", "maya")]
    pp = await _prompt_post(session, admin, reveal=False)
    ruth_answer = await _post(session, ruth, pp)
    assert ruth_answer.id in await _visible(session, maya)


async def test_feed_leaves_daily_question_thread_to_the_card(session: AsyncSession) -> None:
    from app.repositories.post_repo import PostRepository

    admin, ruth, maya = [await _user(session, n) for n in ("admin", "ruth", "maya")]
    daily = await _prompt_post(session, admin, reveal=True)
    weekly = await _prompt_post(session, admin, reveal=False)
    host = (
        await session.execute(select(PromptPost.post_id).where(PromptPost.id == daily))
    ).scalar_one()
    answer = await _post(session, maya, daily)
    other_answer = await _post(session, ruth, weekly)
    plain = await _post(session, ruth)
    items, _ = await PostRepository(session).list_feed(CID, viewer_id=maya.id, limit=100)
    ids = {uuid.UUID(str(i["id"])) for i in items}
    assert plain.id in ids and other_answer.id in ids
    assert answer.id not in ids and host not in ids


async def test_answer_count_drops_when_an_answer_is_deleted(session: AsyncSession) -> None:
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    from app.repositories.prompt_repo import PromptRepository

    admin, ruth, maya = [await _user(session, n) for n in ("admin", "ruth", "maya")]
    pp = await _prompt_post(session, admin, reveal=True)
    a = await _post(session, ruth, pp)
    await _post(session, maya, pp)
    repo = PromptRepository(session)
    await repo.refresh_response_count(pp)

    async def count() -> int:
        row = await session.execute(select(PromptPost.response_count).where(PromptPost.id == pp))
        return int(row.scalar_one())

    assert await count() == 2
    a.deleted_at = _dt.now(_UTC)
    await session.flush()
    await repo.refresh_response_count(pp)
    assert await count() == 1
