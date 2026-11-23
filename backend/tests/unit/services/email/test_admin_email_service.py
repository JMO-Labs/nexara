"""
@file test_admin_email_service.py
@brief Admin SMTP settings: password write-only + encrypted, audit, test send.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import Settings
from app.services.admin_email_service import AdminEmailService

COLS = {
    "id": uuid.uuid4(),
    "smtp_host": None,
    "smtp_port": None,
    "smtp_security": None,
    "smtp_user": None,
    "smtp_password": None,
    "smtp_from": None,
    "smtp_from_name": None,
    "smtp_auth": "password",
    "smtp_google_refresh": None,
    "smtp_last_ok_at": None,
    "smtp_last_error": None,
}
FULL = {
    "host": "smtp.gmail.com",
    "port": 587,
    "security": "starttls",
    "user": "me@gmail.com",
    "password": "abcd efgh ijkl mnop",
    "from_addr": "me@gmail.com",
}


def _svc():
    row = SimpleNamespace(**COLS)

    async def update(_cid, values):
        for k, v in values.items():
            setattr(row, k, v)
        return row

    repo = AsyncMock()
    repo.get.return_value = row
    repo.update_smtp.side_effect = update
    audit = AsyncMock()
    return AdminEmailService(repo, uuid.uuid4(), Settings(), audit), row, audit


async def test_password_encrypted_never_returned_not_audited():
    svc, row, audit = _svc()
    out = await svc.update(FULL)
    assert row.smtp_password and "abcd" not in row.smtp_password
    assert "abcd" not in str(out) and "abcd" not in str(audit.append.await_args)
    assert out["has_password"] and out["configured"] and "password" not in out
    assert audit.append.await_args.kwargs["action"] == "email.settings.updated"
    out = await svc.update({"from_name": "Fam"})  # omitted password kept
    assert out["has_password"] and row.smtp_from_name == "Fam"
    assert "abcd" not in str(await svc.get())


async def test_empty_password_clears():
    svc, row, _ = _svc()
    await svc.update(FULL)
    out = await svc.update({"password": ""})
    assert not out["has_password"] and row.smtp_password is None


async def test_test_failure_returns_error_and_stores_it():
    svc, row, _ = _svc()
    await svc.update(FULL)
    boom = AsyncMock(side_effect=OSError("raw 10.1.2.3 refused"))
    with patch("app.services.admin_email_service.send_email", boom):
        out = await svc.test("to@example.com")
    assert out["ok"] is False and out["category"] == "connect_failed"
    assert "10.1.2.3" not in str(out) and "10.1.2.3" not in row.smtp_last_error
    assert row.smtp_last_error.startswith("connect_failed: ")
    assert boom.await_args.kwargs["record"] is False


async def test_test_success_stamps_ok_and_clears_error():
    svc, row, _ = _svc()
    await svc.update(FULL)
    row.smtp_last_error = "old"
    with patch("app.services.admin_email_service.send_email", AsyncMock()):
        out = await svc.test("to@example.com")
    assert out == {"ok": True, "error": None, "category": None}
    assert row.smtp_last_ok_at is not None and row.smtp_last_error is None


async def test_test_unconfigured():
    svc, _, _ = _svc()
    out = await svc.test("to@example.com")
    assert out["ok"] is False


async def _saved(svc, row):
    await svc.update(FULL)
    row.smtp_google_refresh = "refresh-token"


async def test_retarget_without_password_clears_secrets():
    for change in ({"host": "evil.example.com"}, {"port": 465}, {"user": "other@x.com"}):
        svc, row, _ = _svc()
        await _saved(svc, row)
        out = await svc.update(change)
        assert row.smtp_password is None and row.smtp_google_refresh is None, change
        assert not out["has_password"] and not out["has_google_refresh"]


async def test_retarget_with_new_password_keeps_new_password():
    svc, row, _ = _svc()
    await _saved(svc, row)
    out = await svc.update({"host": "new.example.com", "password": "fresh-pw"})
    assert out["has_password"] and row.smtp_google_refresh is None


async def test_unchanged_target_keeps_secrets():
    svc, row, _ = _svc()
    await _saved(svc, row)
    out = await svc.update(
        {"host": FULL["host"], "port": 587, "user": FULL["user"], "from_name": "Fam"}
    )
    assert out["has_password"] and row.smtp_google_refresh == "refresh-token"


async def test_unreadable_password_test_returns_auth_failed():
    svc, row, _ = _svc()
    await svc.update(FULL)
    row.smtp_password = "garbage-not-fernet"
    out = await svc.test("to@example.com")
    assert out["ok"] is False and out["category"] == "auth_failed"
    assert out["error"] == "Saved password can't be read; re-enter it."
