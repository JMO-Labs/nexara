"""
@file test_post_repo_edited.py
@brief update_content stamps edited_at so clients show "edited" only for real edits.
"""

from unittest.mock import AsyncMock, MagicMock

from app.models.post import Post
from app.repositories.post_repo import PostRepository


async def test_update_content_stamps_edited_at() -> None:
    session = MagicMock(flush=AsyncMock(), refresh=AsyncMock())
    post = MagicMock(spec=Post)
    post.edited_at = None
    await PostRepository(session).update_content(post, "new text")
    assert post.content == "new text"
    assert post.edited_at is not None
