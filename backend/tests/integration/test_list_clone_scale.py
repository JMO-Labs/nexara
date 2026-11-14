"""
@file test_list_clone_scale.py
@brief Real-Postgres scale test: clone a 10k-item list template (nexara#228).
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import NotFoundError
from app.models.community import Community
from app.models.list import List
from app.models.list_template import ListTemplate, ListTemplateField, ListTemplateItem
from app.models.user import User
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_template_repo import ListTemplateRepository
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_template_service import ListTemplateService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
N_ITEMS = 10_000
PAGE = 100
BATCH = 1_000


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(session: AsyncSession) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=COMMUNITY_ID,
        email=f"lcs_{tag}@nexara.dev",
        username=f"lcs_{tag}",
        display_name="clone scale",
    )
    session.add(u)
    await session.flush()
    return u


async def _big_template(session: AsyncSession, author: User) -> uuid.UUID:
    """@brief Create a template with one field and N_ITEMS batch-inserted items."""
    tpl = ListTemplate(community_id=COMMUNITY_ID, author_id=author.id, name="Big")
    tpl.fields = [ListTemplateField(position=0, key="title", label="Title", type_key="text")]
    session.add(tpl)
    await session.flush()
    tpl_id = tpl.id
    for start in range(0, N_ITEMS, BATCH):
        rows = [
            {"template_id": tpl_id, "position": i, "values": {"title": f"item {i}"}}
            for i in range(start, min(start + BATCH, N_ITEMS))
        ]
        await session.execute(insert(ListTemplateItem), rows)
    # Drop cached ORM state so the service loads the template like a fresh request.
    session.expunge_all()
    return tpl_id


def _service(session: AsyncSession) -> ListTemplateService:
    return ListTemplateService(
        ListTemplateRepository(session),
        ListFieldRegistry(),
        list_repo=ListRepository(session),
        item_repo=ListItemRepository(session),
    )


async def test_clone_10k_item_template_is_complete(session: AsyncSession) -> None:
    author = await _user(session)
    tpl_id = await _big_template(session, author)
    tpl_item_ids = set(
        (
            await session.execute(
                select(ListTemplateItem.id).where(ListTemplateItem.template_id == tpl_id)
            )
        ).scalars()
    )
    assert len(tpl_item_ids) == N_ITEMS

    new = await _service(session).clone_template_to_list(COMMUNITY_ID, tpl_id, author.id)

    assert new.item_count == N_ITEMS
    assert new.community_id == COMMUNITY_ID
    assert new.template_id == tpl_id

    repo = ListItemRepository(session)
    seen: list[uuid.UUID] = []
    positions: list[int] = []
    cursor: str | None = None
    while True:
        page, cursor = await repo.list_items_keyset(new.id, cursor=cursor, limit=PAGE)
        assert len(page) <= PAGE
        assert all(it.list_id == new.id for it in page)
        seen.extend(it.id for it in page)
        positions.extend(it.position for it in page)
        if cursor is None:
            break

    assert len(seen) == N_ITEMS
    assert len(set(seen)) == N_ITEMS
    assert not set(seen) & tpl_item_ids
    assert positions == list(range(N_ITEMS))


async def test_clone_is_scoped_to_template_community(session: AsyncSession) -> None:
    author = await _user(session)
    tpl = ListTemplate(community_id=COMMUNITY_ID, author_id=author.id, name="Scoped")
    session.add(tpl)
    other = Community(name=f"other-{uuid.uuid4().hex[:6]}")
    session.add(other)
    await session.flush()

    with pytest.raises(NotFoundError):
        await _service(session).clone_template_to_list(other.id, tpl.id, author.id)

    cloned = (await session.execute(select(List.id).where(List.template_id == tpl.id))).all()
    assert cloned == []
