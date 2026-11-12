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
COMM = uuid.uuid4()
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


def _storage(blobs: dict[str, list[bytes]]) -> MagicMock:
    storage = MagicMock()
    storage.get = AsyncMock()

    def stream(key):
        async def gen():
            for c in blobs[key]:
                yield c

        return gen()

    storage.get_stream = stream
    return storage


async def _build(repo, storage):
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        await build_export_archive(repo, storage, UID, COMM, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            return {n: zf.read(n) for n in zf.namelist()}


class TestBuildArchive:
    async def test_structure_and_contents(self):
        m = _media("a.jpg", "k/a")
        storage = _storage({"k/a": [b"IM", b"G"]})
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
        storage.get.assert_not_called()

    async def test_duplicate_filenames_kept_and_path_stripped(self):
        a, b = _media("x.png", "k/1"), _media("../x.png", "k/2")
        storage = _storage({"k/1": [b"1"], "k/2": [b"2"]})
        files = await _build(_repo([a, b]), storage)
        media_names = [n for n in files if n.startswith("media/")]
        assert len(media_names) == 2
        assert all(".." not in n for n in media_names)

    async def test_media_streamed_in_chunks_without_get(self):
        """Chunks are consumed lazily, one file at a time, never via get()."""
        events: list[str] = []

        def stream(key):
            async def gen():
                events.append(f"open:{key}")
                for c in (b"a", b"b"):
                    yield c
                events.append(f"close:{key}")

            return gen()

        storage = MagicMock()
        storage.get = AsyncMock()
        storage.get_stream = stream
        files = await _build(_repo([_media("a", "k1"), _media("b", "k2")]), storage)
        assert events == ["open:k1", "close:k1", "open:k2", "close:k2"]
        storage.get.assert_not_called()
        assert files["media/a"] == b"ab"


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
