"""
@file test_birthday_tasks_run.py
@brief Unit tests for _send_birthday_reminders_async orchestration.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import birthday_tasks


async def test_one_service_per_community_sums_and_commits_once():
    cids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    svc_cls = MagicMock()
    svc_cls.return_value.send_reminders = AsyncMock(side_effect=[2, 3, 4])
    with (
        patch.object(birthday_tasks, "async_session_factory", factory),
        patch.object(
            birthday_tasks.BirthdayRepository,
            "list_community_ids_with_birthday",
            AsyncMock(return_value=cids),
        ),
        patch.object(birthday_tasks, "BirthdayService", svc_cls),
        patch.object(birthday_tasks, "NotificationService"),
    ):
        result = await birthday_tasks._send_birthday_reminders_async()
    assert result == {"sent": 9}
    assert svc_cls.call_count == 3
    assert [c.args[3] for c in svc_cls.call_args_list] == cids
    session.commit.assert_awaited_once()
