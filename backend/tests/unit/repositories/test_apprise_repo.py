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


async def test_list_for_user_all_includes_disabled() -> None:
    s = _session()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    s.execute.return_value = res
    await AppriseRepository(s).list_for_user(uuid4(), uuid4(), enabled_only=False)
    assert "enabled" not in str(s.execute.call_args.args[0]).split("WHERE")[1]


async def test_set_enabled_toggles_and_resets_failures() -> None:
    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.enabled = False
    row.failure_count = 10
    s.get.return_value = row
    assert await AppriseRepository(s).set_enabled(uuid4(), True) is True
    assert row.enabled is True
    assert row.failure_count == 0


async def test_set_enabled_missing_returns_false() -> None:
    s = _session()
    s.get.return_value = None
    assert await AppriseRepository(s).set_enabled(uuid4(), True) is False


async def test_delete_removes_row() -> None:
    s = _session()
    row = MagicMock(spec=AppriseURL)
    s.get.return_value = row
    assert await AppriseRepository(s).delete(uuid4()) is True
    s.delete.assert_awaited_once_with(row)


async def test_delete_missing_returns_false() -> None:
    s = _session()
    s.get.return_value = None
    assert await AppriseRepository(s).delete(uuid4()) is False


async def test_test_send_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.notifications.secrets import encrypt_url

    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.apprise_url = encrypt_url("json://localhost")
    s.get.return_value = row
    calls: list[dict[str, str]] = []

    def fake_notify(self: object, **kw: str) -> bool:
        calls.append(kw)
        return True

    monkeypatch.setattr("apprise.Apprise.notify", fake_notify)
    ok, msg = await AppriseRepository(s).test_send(uuid4(), "T", "B")
    assert ok is True
    assert calls == [{"body": "B", "title": "T"}]
    assert "json://" not in msg


async def test_test_send_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.notifications.secrets import encrypt_url

    s = _session()
    row = MagicMock(spec=AppriseURL)
    row.apprise_url = encrypt_url("json://localhost")
    s.get.return_value = row

    def boom(self: object, **kw: str) -> bool:
        raise RuntimeError("json://localhost secret")

    monkeypatch.setattr("apprise.Apprise.notify", boom)
    ok, msg = await AppriseRepository(s).test_send(uuid4(), "T", "B")
    assert ok is False
    assert "secret" not in msg


async def test_test_send_missing_row() -> None:
    s = _session()
    s.get.return_value = None
    ok, _msg = await AppriseRepository(s).test_send(uuid4(), "T", "B")
    assert ok is False
