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
    out = await svc.update({"host": "other.example.com"})  # omitted password kept
    assert out["has_password"] and row.smtp_host == "other.example.com"
    assert "abcd" not in str(await svc.get())


async def test_empty_password_clears():
    svc, row, _ = _svc()
    await svc.update(FULL)
    out = await svc.update({"password": ""})
    assert not out["has_password"] and row.smtp_password is None


async def test_test_failure_returns_error_and_stores_it():
    svc, row, _ = _svc()
    await svc.update(FULL)
    boom = AsyncMock(side_effect=OSError("auth failed"))
    with patch("app.services.admin_email_service.send_email", boom):
        out = await svc.test("to@example.com")
    assert out["ok"] is False and "auth failed" in out["error"]
    assert row.smtp_last_error and "auth failed" in row.smtp_last_error
    assert boom.await_args.kwargs["record"] is False


async def test_test_success_stamps_ok_and_clears_error():
    svc, row, _ = _svc()
    await svc.update(FULL)
    row.smtp_last_error = "old"
    with patch("app.services.admin_email_service.send_email", AsyncMock()):
        out = await svc.test("to@example.com")
    assert out == {"ok": True, "error": None}
    assert row.smtp_last_ok_at is not None and row.smtp_last_error is None


async def test_test_unconfigured():
    svc, _, _ = _svc()
    out = await svc.test("to@example.com")
    assert out["ok"] is False
