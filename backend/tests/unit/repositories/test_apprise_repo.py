"""@file Tests for AppriseRepository (encryption at rest, auto-disable)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.models.apprise_url import AppriseURL
from app.repositories.apprise_repo import AUTO_DISABLE_THRESHOLD, AppriseRepository
from app.services.notifications.secrets import decrypt_url


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPRISE_ENCRYPTION_KEY", Fernet.generate_key().decode())


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    s.expunge = MagicMock()
    return s


async def test_create_stores_ciphertext() -> None:
    s = _session()
    repo = AppriseRepository(s)
    row = await repo.create(uuid4(), uuid4(), "slack://a/b/c", label="team")
    assert row.apprise_url != "slack://a/b/c"
    assert decrypt_url(row.apprise_url) == "slack://a/b/c"
    s.add.assert_called_once()
    s.flush.assert_awaited()


async def test_list_for_user_decrypts_on_read() -> None:
    from app.services.notifications.secrets import encrypt_url

    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.apprise_url = encrypt_url("slack://a/b/c")
    res = MagicMock()
    res.scalars.return_value.all.return_value = [row]
    s.execute.return_value = res
    out = await AppriseRepository(s).list_for_user(uuid4(), uuid4())
    assert out[0].apprise_url == "slack://a/b/c"


async def test_record_failure_auto_disables_at_threshold() -> None:
    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.failure_count = AUTO_DISABLE_THRESHOLD - 1
    row.enabled = True
    s.get.return_value = row
    count = await AppriseRepository(s).record_failure(uuid4())
    assert count == AUTO_DISABLE_THRESHOLD
    assert row.enabled is False
    assert row.last_failure_at is not None


async def test_record_success_resets_failures() -> None:
    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.failure_count = 3
    s.get.return_value = row
    await AppriseRepository(s).record_success(uuid4())
    assert row.failure_count == 0


async def test_get_decrypts_and_detaches() -> None:
    from app.services.notifications.secrets import encrypt_url

    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.apprise_url = encrypt_url("slack://a/b/c")
    s.get.return_value = row
    out = await AppriseRepository(s).get(uuid4())
    assert out is row
    assert out.apprise_url == "slack://a/b/c"
    s.expunge.assert_called_once_with(row)


async def test_get_missing_returns_none() -> None:
    s = _session()
    s.get.return_value = None
    assert await AppriseRepository(s).get(uuid4()) is None
    s.expunge.assert_not_called()


async def test_record_failure_missing_row_returns_zero() -> None:
    s = _session()
    s.get.return_value = None
    assert await AppriseRepository(s).record_failure(uuid4()) == 0
    s.flush.assert_not_awaited()
