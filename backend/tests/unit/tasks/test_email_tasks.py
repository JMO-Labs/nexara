"""
@file test_email_tasks.py
@brief Invite and password-reset email tasks: real links, skipped when SMTP unset.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.services.email.smtp_settings import SmtpConfig
from app.tasks import email_tasks as et

CFG = SmtpConfig("h", 587, "starttls", "u", "p", "noreply@example.com")


def _ctx(**kw):
    base = {
        "cfg": CFG,
        "to": "new@example.com",
        "inviter": "Ann",
        "branding": {"community_name": "The Smiths"},
        "sender_name": None,
    }
    return et._MailCtx(**{**base, **kw})


class TestInvite:
    def test_sends_link_with_token_and_subject(self):
        send = AsyncMock()
        with (
            patch.object(et, "_invite_ctx", AsyncMock(return_value=_ctx())),
            patch.object(et, "smtp_send", send),
            patch.object(et, "get_settings") as gs,
        ):
            gs.return_value.APP_BASE_URL = "https://home.example.com/"
            out = et.send_invite_email.apply(args=["iid", "tok123"]).get()
        assert out == {"status": "sent"}
        cfg, to, subject, html, text = send.await_args.args
        assert (cfg, to) == (CFG, "new@example.com")
        assert subject == "Ann invited you to The Smiths"
        assert "https://home.example.com/register?invite=tok123" in html
        assert "tok123" in text

    def test_not_configured_skips_and_logs(self):
        with (
            patch.object(et, "_invite_ctx", AsyncMock(return_value=_ctx(cfg=None))),
            patch.object(et, "smtp_send", AsyncMock()) as send,
            patch.object(et, "logger") as log,
        ):
            out = et.send_invite_email.apply(args=["iid", "t"]).get()
        assert out == {"status": "skipped"}
        send.assert_not_awaited()
        assert log.info.call_args.args[0] == "email.not_configured"

    def test_missing_or_used_invite_skips(self):
        with patch.object(et, "_invite_ctx", AsyncMock(return_value=None)):
            assert et.send_invite_email.apply(args=["iid", "t"]).get() == {"status": "skipped"}


class TestReset:
    def test_sends_reset_link(self):
        send = AsyncMock()
        ctx = _ctx(to="me@example.com", inviter="")
        with (
            patch.object(et, "_reset_ctx", AsyncMock(return_value=ctx)),
            patch.object(et, "smtp_send", send),
            patch.object(et, "get_settings") as gs,
        ):
            gs.return_value.APP_BASE_URL = "https://home.example.com"
            out = et.send_password_reset_email.apply(args=["uid", "rtok"]).get()
        assert out == {"status": "sent"}
        _, to, subject, html, text = send.await_args.args
        assert to == "me@example.com" and subject == "Reset your The Smiths password"
        assert "https://home.example.com/reset-password?token=rtok" in html
        assert "60 minutes" in text

    def test_not_configured(self):
        with (
            patch.object(et, "_reset_ctx", AsyncMock(return_value=_ctx(cfg=None))),
            patch.object(et, "smtp_send", AsyncMock()) as send,
            patch.object(et, "logger") as log,
        ):
            out = et.send_password_reset_email.apply(args=["u", "t"]).get()
        assert out == {"status": "skipped"}
        send.assert_not_awaited()
        assert log.info.call_args.args[0] == "email.not_configured"
