"""
@file test_sender.py
@brief Unit tests for the single SMTP sender (send_email) and resolve_smtp.
"""

from __future__ import annotations

import ssl
import uuid
from datetime import UTC, datetime, timedelta
from email.utils import formataddr
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiosmtplib import errors as smtp_errors

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.services.email.sender import SmtpSendError, classify, send_email
from app.services.email.smtp_settings import SmtpConfig, resolve_smtp


def _cfg(**kw) -> SmtpConfig:
    base = {
        "host": "smtp.example.com",
        "port": 587,
        "security": "starttls",
        "user": "user",
        "password": "secret",
        "from_addr": "noreply@example.com",
    }
    return SmtpConfig(**{**base, **kw})


def _ctx():
    ctx = MagicMock(send_message=AsyncMock())
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


async def _send(cfg, **kw):
    ctx = _ctx()
    with (
        patch("app.services.email.sender.SMTP", return_value=ctx) as smtp,
        patch("app.services.email.sender._record", new=AsyncMock()) as rec,
    ):
        await send_email(cfg, "u@example.com", "S", "<p>x</p>", "x", **kw)
    return smtp, ctx, rec


class TestTransport:
    async def test_587_starttls(self):
        smtp, _, _ = await _send(_cfg())
        kw = smtp.call_args.kwargs
        assert kw["start_tls"] is True and kw["use_tls"] is False
        assert kw["hostname"] == "smtp.example.com" and kw["port"] == 587

    async def test_465_ssl(self):
        smtp, _, _ = await _send(_cfg(port=465, security="ssl"))
        kw = smtp.call_args.kwargs
        assert kw["use_tls"] is True and kw["start_tls"] is False

    async def test_none_security(self):
        smtp, _, _ = await _send(_cfg(port=25, security="none", user="", password=""))
        kw = smtp.call_args.kwargs
        assert kw["use_tls"] is False and kw["start_tls"] is False

    async def test_gmail_password_spaces_stripped(self):
        smtp, _, _ = await _send(_cfg(host="smtp.gmail.com", password="abcd efgh ijkl mnop"))
        assert smtp.call_args.kwargs["password"] == "abcdefghijklmnop"

    async def test_other_host_password_untouched(self):
        smtp, _, _ = await _send(_cfg(password="a b"))
        assert smtp.call_args.kwargs["password"] == "a b"


class TestHeaders:
    async def test_display_name_and_reply_to(self):
        _, ctx, _ = await _send(_cfg(), sender_name="Família Silva", reply_to="r+t@e.com")
        msg = ctx.send_message.call_args.args[0]
        assert msg["From"] == formataddr(("Família Silva", "noreply@example.com"))
        assert msg["Reply-To"] == "r+t@e.com"

    async def test_cfg_from_name_used_and_plain_from(self):
        _, ctx, _ = await _send(_cfg(from_name="Fam"))
        assert "Fam" in ctx.send_message.call_args.args[0]["From"]
        _, ctx, _ = await _send(_cfg())
        msg = ctx.send_message.call_args.args[0]
        assert msg["From"] == "noreply@example.com" and msg["Reply-To"] is None

    async def test_list_unsubscribe(self):
        _, ctx, _ = await _send(_cfg(), list_unsubscribe="<http://u>")
        assert ctx.send_message.call_args.args[0]["List-Unsubscribe"] == "<http://u>"


class TestStatus:
    async def test_success_recorded(self):
        _, _, rec = await _send(_cfg(community_id="cid"))
        assert rec.await_args.args[1] is None

    async def test_failure_recorded_generic_and_raised(self):
        ctx = _ctx()
        ctx.send_message.side_effect = OSError("secret leaked host=10.0.0.5")
        with (
            patch("app.services.email.sender.SMTP", return_value=ctx),
            patch("app.services.email.sender._record", new=AsyncMock()) as rec,
            pytest.raises(SmtpSendError) as ei,
        ):
            await send_email(_cfg(password="secret"), "u@e.com", "S", "<p>x</p>", "x")
        assert ei.value.category == "connect_failed"
        stored = rec.await_args.args[1]
        assert stored.startswith("connect_failed: ") and "10.0.0.5" not in stored
        assert "secret" not in str(ei.value)

    async def test_record_false_skips(self):
        ctx = _ctx()
        with (
            patch("app.services.email.sender.SMTP", return_value=ctx),
            patch("app.services.email.sender._record", new=AsyncMock()) as rec,
        ):
            await send_email(_cfg(), "u@e.com", "S", "<p>x</p>", "x", record=False)
        rec.assert_not_awaited()


class TestResolve:
    def _session(self, row):
        s = AsyncMock()
        s.get.return_value = row
        return s

    async def test_db_wins(self):
        key = derive_fernet_key(Settings().SECRET_KEY)
        row = SimpleNamespace(
            id="cid",
            smtp_host="db.example.com",
            smtp_port=465,
            smtp_security="ssl",
            smtp_user="u",
            smtp_password=encrypt_secret("pw", key),
            smtp_from="f@example.com",
            smtp_from_name="N",
            smtp_auth="password",
            smtp_google_refresh=None,
        )
        with patch("app.services.email.smtp_settings.get_settings", return_value=Settings()):
            cfg = await resolve_smtp(self._session(row), "cid")
        assert cfg.host == "db.example.com" and cfg.password == "pw" and cfg.security == "ssl"

    async def test_env_fallback_infers_security(self):
        row = SimpleNamespace(smtp_host=None)
        env = Settings(SMTP_HOST="e.example.com", SMTP_PORT=465, SMTP_FROM="a@e.com")
        with patch("app.services.email.smtp_settings.get_settings", return_value=env):
            cfg = await resolve_smtp(self._session(row), "cid")
            assert cfg.security == "ssl" and cfg.from_addr == "a@e.com"
            env.SMTP_PORT = 587
            assert (await resolve_smtp(self._session(row), "cid")).security == "starttls"

    async def test_none_when_unconfigured(self):
        with patch("app.services.email.smtp_settings.get_settings", return_value=Settings()):
            assert await resolve_smtp(self._session(SimpleNamespace(smtp_host=None)), "c") is None


class TestNoPlaintextCredentials:
    async def test_none_security_with_credentials_refused(self):
        ctx = _ctx()
        with (
            patch("app.services.email.sender.SMTP", return_value=ctx) as smtp,
            patch("app.services.email.sender._record", new=AsyncMock()),
            pytest.raises(SmtpSendError, match="without encryption"),
        ):
            await send_email(_cfg(security="none", port=25), "u@e.com", "S", "<p>x</p>")
        smtp.assert_not_called()

    async def test_none_security_without_credentials_ok(self):
        smtp, _, _ = await _send(_cfg(security="none", port=25, user="", password=""))
        smtp.assert_called_once()

    async def test_unreadable_secret_refused(self):
        with (
            patch("app.services.email.sender.SMTP") as smtp,
            patch("app.services.email.sender._record", new=AsyncMock()),
            pytest.raises(SmtpSendError) as ei,
        ):
            await send_email(_cfg(secret_unreadable=True), "u@e.com", "S", "<p>x</p>")
        assert ei.value.category == "auth_failed" and "re-enter" in ei.value.message
        smtp.assert_not_called()


@pytest.mark.parametrize(
    ("exc", "cat"),
    [
        (smtp_errors.SMTPAuthenticationError(535, "bad"), "auth_failed"),
        (smtp_errors.SMTPConnectError("nope"), "connect_failed"),
        (smtp_errors.SMTPServerDisconnected("gone"), "connect_failed"),
        (ConnectionRefusedError(), "connect_failed"),
        (smtp_errors.SMTPConnectTimeoutError("t"), "timeout"),
        (smtp_errors.SMTPReadTimeoutError("t"), "timeout"),
        (TimeoutError(), "timeout"),
        (ssl.SSLError("x"), "tls_failed"),
        (smtp_errors.SMTPNotSupported("no starttls"), "tls_failed"),
        (smtp_errors.SMTPRecipientRefused(550, "no", "a@b.c"), "rejected"),
        (smtp_errors.SMTPSenderRefused(550, "no", "a@b.c"), "rejected"),
        (smtp_errors.SMTPDataError(554, "spam"), "rejected"),
        (ValueError("?"), "unknown"),
    ],
)
def test_classify(exc, cat):
    assert classify(exc).category == cat


class TestRecordThrottle:
    """@brief _record writes only on status change or a stale success."""

    def _factory(self, last_ok, last_err):
        session = AsyncMock()
        session.execute.return_value = MagicMock(
            one_or_none=MagicMock(return_value=(last_ok, last_err))
        )
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return factory, session

    async def _run(self, last_ok, last_err, error):
        from app.services.email import sender

        factory, session = self._factory(last_ok, last_err)
        with patch("app.db.session.async_session_factory", factory):
            await sender._record(uuid.uuid4(), error)
        return session.commit.await_count  # 1 = written, 0 = skipped

    async def test_recent_ok_skipped(self):
        assert await self._run(datetime.now(UTC) - timedelta(minutes=1), None, None) == 0

    async def test_old_ok_written(self):
        assert await self._run(datetime.now(UTC) - timedelta(minutes=11), None, None) == 1

    async def test_error_to_ok_written(self):
        assert await self._run(datetime.now(UTC), "auth_failed: x", None) == 1

    async def test_ok_to_error_written_same_error_skipped(self):
        assert await self._run(datetime.now(UTC), None, "timeout: x") == 1
        assert await self._run(datetime.now(UTC), "timeout: x", "timeout: x") == 0


class TestDecryptFailure:
    async def test_bad_ciphertext_flags_unreadable(self):
        from app.services.email.smtp_settings import config_from_row

        row = SimpleNamespace(
            id="cid",
            smtp_host="h",
            smtp_port=587,
            smtp_security="starttls",
            smtp_user="u",
            smtp_password="not-fernet",
            smtp_from=None,
            smtp_from_name=None,
            smtp_auth="password",
            smtp_google_refresh=None,
        )
        cfg = config_from_row(row, "k")
        assert cfg.secret_unreadable and cfg.password == ""


async def test_client_secret_scrubbed_from_logs():
    from app.services.email.sender import _fail

    cfg = _cfg(google_client_secret="CSEC-123")
    err = SmtpSendError("connect_failed")
    with patch("app.services.email.sender.logger") as log:
        with pytest.raises(SmtpSendError):
            await _fail(cfg, False, err, RuntimeError("boom CSEC-123 end"))
    assert "CSEC-123" not in log.error.call_args.kwargs["detail"]
