"""
@file test_sassybot.py
@brief Unit tests for SassybotService and the sassybot Celery task logic.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.community import Community
from app.models.media import Media
from app.models.post import Post
from app.models.user import User
from app.repositories.sassybot_repo import SassybotRepository
from app.services.ai.provider import AIProvider
from app.services.ai.sassybot_service import MAX_THREAD_COMMENTS, SassybotService, wants_sassybot
from app.services.storage.base import StorageBackend

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
BOT = uuid.uuid4()


def _make(*, opt_out=False, sass=2, prob=15, invoke_only=False, images=0, depth=0):
    post = MagicMock(spec=Post)
    post.id = uuid.uuid4()
    post.content = "x" * 600
    post.created_at = MagicMock()
    post.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    author = MagicMock(spec=User)
    author.sassybot_opt_out = opt_out
    community = MagicMock(spec=Community)
    community.sassybot_sass_level = sass
    community.sassybot_probability = prob
    community.sassybot_invoke_only = invoke_only
    community.sassybot_enabled = True
    media = []
    for _ in range(images):
        m = MagicMock(spec=Media)
        m.content_type = "image/png"
        m.storage_key = "k"
        media.append(m)
    repo = AsyncMock(spec=SassybotRepository)
    repo.get_post_and_author.return_value = (post, author)
    repo.get_community.return_value = community
    repo.get_community_id_for_post.return_value = CID
    repo.get_images.return_value = media
    repo.count_bot_comments.return_value = depth
    provider = AsyncMock(spec=AIProvider)
    provider.complete.return_value = ("  Nice one!  ", 0.1, 5)
    provider.vision.return_value = ("a cat on a sofa", 0.1, 5)
    storage = AsyncMock(spec=StorageBackend)
    storage.get.return_value = b"img"
    svc = SassybotService(repo, provider, storage, BOT)
    return svc, repo, provider, post


async def test_opt_out_returns_none() -> None:
    svc, _, provider, post = _make(opt_out=True)
    assert await svc.generate_comment(post.id, CID) is None
    provider.complete.assert_not_called()


@pytest.mark.parametrize(("level", "word"), [(1, "mild"), (2, "moderate"), (3, "spicy")])
async def test_sass_level_in_prompt(level: int, word: str) -> None:
    svc, _, provider, post = _make(sass=level)
    assert await svc.generate_comment(post.id, CID) == "Nice one!"
    prompt = provider.complete.call_args.args[0]
    assert word in prompt
    assert "x" * 500 in prompt
    assert "x" * 501 not in prompt


async def test_vision_context_included() -> None:
    svc, _, provider, post = _make(images=2)
    await svc.generate_comment(post.id, CID)
    assert provider.vision.await_count == 2
    assert "a cat on a sofa" in provider.complete.call_args.args[0]


async def test_no_images_no_vision() -> None:
    svc, _, provider, post = _make()
    await svc.generate_comment(post.id, CID)
    provider.vision.assert_not_called()


async def test_thread_depth_counts_bot_comments() -> None:
    svc, repo, _, post = _make(depth=3)
    assert await svc.count_thread_depth(post.id) == 3
    repo.count_bot_comments.assert_awaited_once_with(post.id, BOT)
    assert MAX_THREAD_COMMENTS == 3


async def test_generate_comment_truncates_to_200() -> None:
    svc, _, provider, post = _make()
    provider.complete.return_value = ("y" * 300, 0.1, 5)
    out = await svc.generate_comment(post.id, CID)
    assert out is not None and len(out) <= 200


async def test_should_trigger_probability(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, _, _, post = _make(prob=15)
    monkeypatch.setattr("app.services.ai.sassybot_service.random.uniform", lambda a, b: 14.9)
    assert await svc.should_trigger(post.id) is True
    monkeypatch.setattr("app.services.ai.sassybot_service.random.uniform", lambda a, b: 15.0)
    assert await svc.should_trigger(post.id) is False


async def test_should_trigger_invoke_only_false() -> None:
    svc, _, _, post = _make(prob=100, invoke_only=True)
    assert await svc.should_trigger(post.id) is False


async def test_should_trigger_zero_prob() -> None:
    svc, _, _, post = _make(prob=0)
    assert await svc.should_trigger(post.id) is False


def test_wants_sassybot_mention() -> None:
    assert wants_sassybot("hey @sassybot roast me")
    assert wants_sassybot("@Sassybot!")
    assert not wants_sassybot("email a@sassybots.com")
    assert not wants_sassybot("nothing")
