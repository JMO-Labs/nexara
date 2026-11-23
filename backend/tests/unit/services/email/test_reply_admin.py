"""
@file test_reply_admin.py
@brief Reply-by-email admin: password write-only + encrypted; test button; poll gating.
"""

from __future__ import annotations

import imaplib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import Settings
from app.services.email_reply_admin_service import EmailReplyAdminService

COLS = {
    "inbound_imap_host": None,
    "inbound_imap_port": 993,
    "inbound_imap_user": None,
    "inbound_imap_password": None,
    "inbound_reply_address": None,
}


def _svc():
    row = SimpleNamespace(**COLS)

    async def update(_cid, values):
        for k, v in values.items():
            setattr(row, k, v)
        return row

    repo = AsyncMock()
    repo.get.return_value = row
    repo.update_inbound.side_effect = update
    audit = AsyncMock()
    return EmailReplyAdminService(repo, uuid.uuid4(), Settings(), audit), row, audit


FULL = {
    "imap_host": "imap.example.com",
    "imap_user": "bot@example.com",
    "imap_password": "hunter2-pw",
    "reply_address": "reply@example.com",
}


async def test_password_encrypted_never_returned_not_audited():
    svc, row, audit = _svc()
    out = await svc.update(FULL)
    assert row.inbound_imap_password and "hunter2" not in row.inbound_imap_password
    assert "hunter2" not in str(out) and "hunter2" not in str(audit.append.await_args)
    assert out["has_password"] and out["configured"] and out["imap_port"] == 993
    out = await svc.update({"imap_host": ""})  # omitted password is kept
    assert out["has_password"] and not out["configured"]
    assert "hunter2" not in str(await svc.get())


async def test_test_button_outcomes():
    svc, *_ = _svc()
    assert (await svc.test())["success"] is False  # not configured
    await svc.update(FULL)
    with patch("app.services.email.imap_client.check") as chk:
        assert (await svc.test())["success"] is True
        assert chk.call_args.args[3] == "hunter2-pw"
        chk.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED hunter2-pw")
        out = await svc.test()
        assert not out["success"] and "hunter2" not in str(out)
        chk.side_effect = OSError("down")
        assert "reach" in (await svc.test())["message"]
