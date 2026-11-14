"""
@file test_sassybot_repo_count.py
@brief count_bot_comments must build a valid query (comments are not soft-deletable).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.repositories.sassybot_repo import SassybotRepository

CID = uuid.uuid4()


async def test_count_bot_comments_builds_valid_query():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 3
    session.execute.return_value = result
    repo = SassybotRepository(session)

    assert await repo.count_bot_comments(uuid.uuid4(), uuid.uuid4(), CID) == 3
    sql = str(session.execute.await_args.args[0]).lower()
    assert "comments.community_id" in sql
    assert "deleted_at" not in sql
