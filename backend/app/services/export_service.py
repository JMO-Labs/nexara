"""
@file export_service.py
@brief Assembles a user's personal-data ZIP archive.
"""

from __future__ import annotations

import json
import posixpath
import uuid
import zipfile
from typing import IO, Any

from app.repositories.export_data_repo import ExportDataRepository
from app.services.storage.base import StorageBackend


def _media_name(filename: str, media_id: str, used: set[str]) -> str:
    """@brief Safe, unique archive path under ``media/`` keeping the original name."""
    base = posixpath.basename(filename.replace("\\", "/")) or media_id
    name = base if base not in used else f"{media_id}_{base}"
    used.add(name)
    return f"media/{name}"


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


async def build_export_archive(
    repo: ExportDataRepository,
    storage: StorageBackend,
    user_id: uuid.UUID,
    fileobj: IO[bytes],
) -> None:
    """
    @brief Write the export ZIP into ``fileobj``.

    Media are fetched and written one at a time so at most one file is held
    in memory; the archive itself is written to the (temp) file object.
    @param repo Data source for the user's rows.
    @param storage Storage backend providing media bytes.
    @param user_id Owner of the data.
    @param fileobj Writable binary file (e.g. NamedTemporaryFile).
    """
    media = await repo.list_media(user_id)
    sections = {
        "profile.json": await repo.get_profile(user_id),
        "posts.json": await repo.list_posts(user_id),
        "comments.json": await repo.list_comments(user_id),
        "reactions.json": await repo.list_reactions(user_id),
        "events.json": await repo.list_events(user_id),
        "rsvps.json": await repo.list_rsvps(user_id),
        "media_metadata.json": media,
    }
    with zipfile.ZipFile(fileobj, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in sections.items():
            zf.writestr(name, _dump(data))
        used: set[str] = set()
        for m in media:
            path = _media_name(m["filename"], m["id"], used)
            zf.writestr(path, await storage.get(m["storage_key"]))
