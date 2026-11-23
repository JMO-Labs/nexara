"""
@file test_newsletter_db.py
@brief Real-Postgres: newsletter is per viewer; pins reorder, hides remove,
       and neither can reveal a post the viewer may not open.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import NotFoundError
from app.models.post import Comment, Post, PostMedia
from app.models.prompt import Prompt, PromptPost
from app.models.recipe import Recipe
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.services.newsletter_service import NewsletterService

URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(UTC)
MONTH = f"{NOW.year}-{NOW.month:02d}"


@pytest.fixture
async def session():
    engine = create_async_engine(URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str, role: str = "member") -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"nl_{name}_{sfx}@nexara.dev", username=f"nl_{name}_{sfx}",
        display_name=name, role=role,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _post(s: AsyncSession, author: User, text: str, **kw: object) -> Post:
    p = Post(community_id=CID, author_id=author.id, content=text, **kw)
    s.add(p)
    await s.flush()
    return p


def _ids(n: object) -> list[uuid.UUID]:
    return [p.id for p in n.top_posts]  # type: ignore[attr-defined]


async def test_group_post_absent_for_non_member(session: AsyncSession) -> None:
    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    g = Subgroup(community_id=CID, name="Book club", slug=f"bc-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    session.add(SubgroupMember(community_id=CID, subgroup_id=g.id, user_id=ruth.id))
    secret = await _post(session, ruth, "club only", visibility="subgroup", subgroup_id=g.id)
    open_ = await _post(session, ruth, "hello all")
    svc = NewsletterService(session, CID)
    assert secret.id in _ids(await svc.build(MONTH, ruth))
    got = _ids(await svc.build(MONTH, maya))
    assert open_.id in got and secret.id not in got


async def test_hidden_removed_pinned_first_and_pin_cannot_reveal(session: AsyncSession) -> None:
    admin, ruth, maya = (
        await _user(session, "adm", "admin"),
        await _user(session, "ruth"),
        await _user(session, "maya"),
    )
    g = Subgroup(community_id=CID, name="Club", slug=f"c-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    popular = await _post(session, ruth, "popular")
    quiet = await _post(session, ruth, "quiet")
    gone = await _post(session, ruth, "gone")
    private_grp = await _post(session, ruth, "group", visibility="subgroup", subgroup_id=g.id)
    session.add(Comment(community_id=CID, post_id=popular.id, author_id=maya.id, content="c"))
    await session.flush()
    svc = NewsletterService(session, CID)
    assert _ids(await svc.build(MONTH, maya))[:2] == [popular.id, quiet.id] or popular.id in _ids(
        await svc.build(MONTH, maya)
    )
    await svc.set_override(MONTH, admin, quiet.id, "pin")
    await svc.set_override(MONTH, admin, gone.id, "hide")
    got = await svc.build(MONTH, maya)
    assert _ids(got)[0] == quiet.id and got.top_posts[0].pinned
    assert gone.id not in _ids(got) and got.hidden_posts == []
    adm = await svc.build(MONTH, admin)
    assert [p.id for p in adm.hidden_posts] == [gone.id]
    # admin (not a member) cannot pin a post they can't open, and a stale pin never reveals it
    with pytest.raises(NotFoundError):
        await svc.set_override(MONTH, admin, private_grp.id, "pin")
    session.add(SubgroupMember(community_id=CID, subgroup_id=g.id, user_id=ruth.id))
    await session.flush()
    await svc.set_override(MONTH, ruth, private_grp.id, "pin")
    assert private_grp.id not in _ids(await svc.build(MONTH, maya))
    await svc.set_override(MONTH, admin, gone.id, None)
    assert gone.id in _ids(await svc.build(MONTH, maya))


async def test_unlocked_daily_answer_gate(session: AsyncSession) -> None:
    admin, ruth, maya = (
        await _user(session, "adm", "admin"),
        await _user(session, "ruth"),
        await _user(session, "maya"),
    )
    prompt = Prompt(
        community_id=CID, title="Q", body="Q?", frequency_type="daily", created_by=admin.id,
        prompt_type="daily_question", reveal_after_answer=True,
    )  # fmt: skip
    session.add(prompt)
    await session.flush()
    host = await _post(session, admin, "Q?")
    pp = PromptPost(
        community_id=CID, prompt_id=prompt.id, post_id=host.id, fired_at=date.today(),
        expires_at=NOW + timedelta(days=1),
    )  # fmt: skip
    session.add(pp)
    await session.flush()
    answer = await _post(session, ruth, "my answer", reply_to_prompt_id=pp.id)
    svc = NewsletterService(session, CID)
    assert answer.id not in _ids(await svc.build(MONTH, maya))
    await _post(session, maya, "mine", reply_to_prompt_id=pp.id)
    assert answer.id in _ids(await svc.build(MONTH, maya))


async def test_recipe_visibility_and_month_rules(session: AsyncSession) -> None:
    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    g = Subgroup(community_id=CID, name="G", slug=f"g-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    session.add_all([
        Recipe(community_id=CID, author_id=ruth.id, title="Open soup"),
        Recipe(
            community_id=CID, author_id=ruth.id, title="Club cake",
            visibility="subgroup", subgroup_id=g.id,
        ),
    ])  # fmt: skip
    await session.flush()
    svc = NewsletterService(session, CID)
    titles = [r.title for r in (await svc.build(MONTH, maya)).new_recipes]
    assert "Open soup" in titles and "Club cake" not in titles
    nxt = NOW + timedelta(days=40)
    for bad in (f"{nxt.year}-{nxt.month:02d}", "1999-01", "2026-13", "nope"):
        with pytest.raises(NotFoundError):
            await svc.build(bad, maya)


async def test_photos_only_from_visible_posts(session: AsyncSession) -> None:
    from app.models.media import Media

    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    g = Subgroup(community_id=CID, name="G2", slug=f"g2-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    media = []
    for i in range(2):
        m = Media(
            community_id=CID, uploader_id=ruth.id, filename="a.jpg", content_type="image/jpeg",
            storage_key=f"nl/{uuid.uuid4()}", size_bytes=1, status="ready",
        )  # fmt: skip
        session.add(m)
        media.append(m)
    await session.flush()
    open_ = await _post(session, ruth, "open pic")
    grp = await _post(session, ruth, "group pic", visibility="subgroup", subgroup_id=g.id)
    session.add_all([
        PostMedia(post_id=open_.id, media_id=media[0].id),
        PostMedia(post_id=grp.id, media_id=media[1].id),
    ])  # fmt: skip
    await session.flush()
    got = await NewsletterService(session, CID).build(MONTH, maya)
    assert [p.media_id for p in got.photos] == [media[0].id]
