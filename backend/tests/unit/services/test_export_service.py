"""
@file test_export_service.py
@brief Unit tests for the user data export archive builder.
"""

from __future__ import annotations

import json
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.media import Media
from app.models.post import Comment, Post, Reaction
from app.models.serialization import serialize
from app.models.user import User
from app.repositories.export_data_repo import ExportDataRepository
from app.services.export_service import build_export_archive

UID = uuid.uuid4()
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _user() -> User:
    u = MagicMock(spec=User)
    u.id = UID
    return u


def _repo(media: list | None = None) -> AsyncMock:
    repo = AsyncMock(spec=ExportDataRepository)
    repo.list_posts.return_value = [{"id": "p1", "content": "hi"}]
    repo.list_comments.return_value = [{"id": "c1"}]
    repo.list_reactions.return_value = [{"id": "r1"}]
    repo.list_events.return_value = [{"id": "e1"}]
    repo.list_rsvps.return_value = [{"id": "s1"}]
    repo.get_profile.return_value = {
        "id": str(UID),
        "email": "a@b.c",
    }
    repo.list_media.return_value = media or []
    return repo


def _media(name: str, key: str) -> dict:
    return {"id": str(uuid.uuid4()), "filename": name, "storage_key": key}


async def _build(repo, storage):
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        await build_export_archive(repo, storage, UID, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            return {n: zf.read(n) for n in zf.namelist()}


class TestBuildArchive:
    async def test_structure_and_contents(self):
        m = _media("a.jpg", "k/a")
        storage = AsyncMock()
        storage.get.return_value = b"IMG"
        files = await _build(_repo([m]), storage)
        assert {
            "profile.json",
            "posts.json",
            "comments.json",
            "reactions.json",
            "events.json",
            "rsvps.json",
            "media_metadata.json",
            "media/a.jpg",
        } <= set(files)
        assert files["media/a.jpg"] == b"IMG"
        assert json.loads(files["posts.json"]) == [{"id": "p1", "content": "hi"}]
        storage.get.assert_awaited_once_with("k/a")

    async def test_duplicate_filenames_kept_and_path_stripped(self):
        a, b = _media("x.png", "k/1"), _media("../x.png", "k/2")
        storage = AsyncMock()
        storage.get.side_effect = [b"1", b"2"]
        files = await _build(_repo([a, b]), storage)
        media_names = [n for n in files if n.startswith("media/")]
        assert len(media_names) == 2
        assert all(".." not in n for n in media_names)

    async def test_media_fetched_one_at_a_time(self):
        storage = AsyncMock()
        storage.get.return_value = b"z"
        await _build(_repo([_media("a", "k1"), _media("b", "k2")]), storage)
        assert storage.get.await_count == 2


class TestSerialize:
    def test_excludes_sensitive_and_formats_values(self):
        u = User(
            id=UID,
            email="e",
            username="u",
            display_name="d",
            password_hash="h",
            totp_secret="t",
            created_at=NOW,
        )
        out = serialize(u)
        assert "password_hash" not in out and "totp_secret" not in out
        assert out["id"] == str(UID)
        assert out["created_at"] == NOW.isoformat()

    @pytest.mark.parametrize("model", [Post, Comment, Reaction, Media])
    def test_models_serialize(self, model):
        assert isinstance(serialize(model()), dict)
