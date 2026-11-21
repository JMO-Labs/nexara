"""
@file test_list_template_listing.py
@brief Listed templates must carry loaded fields/items: GET /list_templates
       500'd with MissingGreenlet when serialization lazy-loaded them.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.list_template import ListTemplate, ListTemplateField
from app.models.user import User
from app.repositories.list_template_repo import ListTemplateRepository
from app.schemas.list_template import ListTemplateOut

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)


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


async def test_listed_templates_serialize_without_lazy_loads(session: AsyncSession) -> None:
    c = Community(name=f"tpl-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    tag = uuid.uuid4().hex[:6]
    author = User(
        community_id=c.id, email=f"tpl_{tag}@nexara.dev", username=f"tpl_{tag}", display_name="t"
    )
    session.add(author)
    await session.flush()
    tpl = ListTemplate(community_id=c.id, author_id=author.id, name="Groceries")
    tpl.fields = [ListTemplateField(position=0, key="item", label="Item", type_key="text")]
    session.add(tpl)
    await session.flush()
    session.expunge_all()  # force a fresh load, as a real request would

    rows, _ = await ListTemplateRepository(session).list_for_community(c.id, author.id)
    out = [ListTemplateOut.model_validate(r) for r in rows]
    assert [f.key for f in out[0].fields] == ["item"]
