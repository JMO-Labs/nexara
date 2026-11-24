"""
@file test_two_factor.py
@brief TwoFactorService lifecycle, AdminSecurityService and migration helpers.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest

from app.core.config import Settings
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.security import hash_password
from app.services.admin_security_service import AdminSecurityService
from app.services.auth.two_factor import TwoFactorService, open_secret, seal_secret

S = Settings(SECRET_KEY="tf-test", JWT_ALGORITHM="HS256")
TR = "app.services.auth.two_factor."


def _user(**kw):
    u = MagicMock()
    u.id, u.email, u.role = uuid.uuid4(), "a@b.c", "member"
    u.community_id = uuid.uuid4()
    u.password_hash = hash_password("right-password1")
    u.totp_enabled, u.totp_secret, u.totp_pending_secret = False, None, None
    u.two_factor_required_since = None
    for k, v in kw.items():
        setattr(u, k, v)
    return u


def _svc(user):
    users, repo, audit = AsyncMock(), AsyncMock(), AsyncMock()
    repo.session = MagicMock()
    return TwoFactorService(users, repo, audit, S, user, "1.2.3.4"), users, repo, audit


@pytest.fixture(autouse=True)
def _valkey():
    with (
        patch(TR + "reserve_attempt", AsyncMock(return_value=True)),
        patch(TR + "claim_totp_code", AsyncMock(return_value=True)),
        patch(TR + "clear_user_attempts", AsyncMock()),
    ):
        yield


async def test_start_stores_pending_encrypted_not_active():
    svc, users, _, _ = _svc(_user())
    out = await svc.start()
    kw = users.update_totp.await_args.kwargs
    assert set(kw) == {"totp_pending_secret"} and kw["totp_pending_secret"] != out["secret"]
    assert open_secret(kw["totp_pending_secret"], S) == out["secret"]


async def test_start_refused_when_enabled():
    svc, *_ = _svc(_user(totp_enabled=True))
    with pytest.raises(AuthorizationError, match="2fa_already_enabled"):
        await svc.start()


async def test_confirm_wrong_code_400_not_enabled():
    sec = pyotp.random_base32()
    svc, users, repo, _ = _svc(_user(totp_pending_secret=seal_secret(sec, S)))
    with pytest.raises(AppError) as e:
        await svc.confirm("000000")
    assert e.value.status_code == 400
    users.update_totp.assert_not_called()
    repo.replace_recovery_codes.assert_not_called()


async def test_confirm_ok_enables_and_issues_ten_codes_and_audits():
    sec = pyotp.random_base32()
    pending = seal_secret(sec, S)
    svc, users, repo, audit = _svc(_user(totp_pending_secret=pending))
    codes = await svc.confirm(pyotp.TOTP(sec).now())
    assert len(codes) == 10
    assert users.update_totp.await_args.kwargs == {
        "totp_secret": pending,
        "totp_pending_secret": None,
        "totp_enabled": True,
    }
    repo.replace_recovery_codes.assert_awaited_once()
    assert audit.append.await_args.kwargs["action"] == "2fa.enabled"


async def test_confirm_without_start_400():
    svc, *_ = _svc(_user())
    with pytest.raises(AppError) as e:
        await svc.confirm("123456")
    assert e.value.status_code == 400


async def test_disable_needs_valid_proof():
    sec = pyotp.random_base32()
    svc, users, _, _ = _svc(_user(totp_enabled=True, totp_secret=seal_secret(sec, S)))
    with pytest.raises(AppError):
        await svc.disable("wrong-password", None)
    with pytest.raises(AppError):
        await svc.disable(None, "000000")
    with pytest.raises(AppError):
        await svc.disable(None, None)
    users.update_totp.assert_not_called()


async def test_disable_with_password_and_with_code():
    sec = pyotp.random_base32()
    svc, users, repo, audit = _svc(_user(totp_enabled=True, totp_secret=seal_secret(sec, S)))
    await svc.disable("right-password1", None)
    assert users.update_totp.await_args.kwargs["totp_enabled"] is False
    assert users.update_totp.await_args.kwargs["totp_secret"] is None
    repo.delete_recovery_codes.assert_awaited_once()
    assert audit.append.await_args.kwargs["action"] == "2fa.disabled"
    svc2, users2, *_ = _svc(_user(totp_enabled=True, totp_secret=seal_secret(sec, S)))
    await svc2.disable(None, pyotp.TOTP(sec).now())
    users2.update_totp.assert_awaited_once()


async def test_disable_with_recovery_code():
    svc, users, *_ = _svc(_user(totp_enabled=True, totp_secret=seal_secret("JBSWY3DPEHPK3PXP", S)))
    with patch(TR + "consume_backup_code", AsyncMock(return_value=True)):
        await svc.disable(None, "abcd1234")
    users.update_totp.assert_awaited_once()


async def test_regenerate_replaces_codes_only_with_valid_code():
    sec = pyotp.random_base32()
    svc, _, repo, audit = _svc(_user(totp_enabled=True, totp_secret=seal_secret(sec, S)))
    with pytest.raises(AppError):
        await svc.regenerate("000000")
    repo.replace_recovery_codes.assert_not_called()
    codes = await svc.regenerate(pyotp.TOTP(sec).now())
    assert len(codes) == 10
    repo.replace_recovery_codes.assert_awaited_once_with(svc._user.id, codes)
    assert audit.append.await_args.kwargs["action"] == "2fa.recovery_regenerated"


async def test_regenerate_when_totp_off_rejected():
    svc, _, repo, _ = _svc(_user())
    with pytest.raises(AppError):
        await svc.regenerate("123456")
    repo.replace_recovery_codes.assert_not_called()


async def test_attempt_cap_is_429():
    svc, *_ = _svc(_user(totp_pending_secret=seal_secret("JBSWY3DPEHPK3PXP", S)))
    with patch(TR + "reserve_attempt", AsyncMock(return_value=False)):
        with pytest.raises(AppError) as e:
            await svc.confirm("123456")
    assert e.value.status_code == 429


async def test_status_shape_and_required():
    from datetime import UTC, datetime

    since = datetime(2026, 1, 1, tzinfo=UTC)
    svc, _, repo, _ = _svc(_user(role="admin", two_factor_required_since=since))
    repo.count_passkeys.return_value = 0
    repo.count_recovery_left.return_value = 0
    repo.get_policy.return_value = "admins"
    st = await svc.status()
    assert st["required"] is True and st["totp"] is False and st["grace_until"] > since
    repo.count_passkeys.return_value = 1
    assert (await svc.status())["required"] is False
    repo.get_policy.return_value = "off"
    assert (await svc.status())["grace_until"] is None


async def test_admin_reset_clears_all_and_audits():
    users, repo, audit = AsyncMock(), AsyncMock(), AsyncMock()
    cid, actor, target = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    svc = AdminSecurityService(users, repo, audit, cid, actor, "1.1.1.1")
    await svc.reset_2fa(target)
    assert users.update_totp.await_args.kwargs["totp_secret"] is None
    repo.delete_recovery_codes.assert_awaited_once_with(target)
    repo.delete_passkeys.assert_awaited_once_with(target, cid)
    assert audit.append.await_args.kwargs["action"] == "admin.user.2fa_reset"
    users.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await svc.reset_2fa(target)


def _migration():
    p = Path(__file__).parents[4] / "alembic/versions/0070_twofactor.py"
    spec = importlib.util.spec_from_file_location("m0070", p)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_migration_encrypt_is_idempotent_and_round_trips():
    from app.core.encryption import derive_fernet_key

    m, key = _migration(), derive_fernet_key("k")
    enc = m._enc("JBSWY3DPEHPK3PXP", key)
    assert enc != "JBSWY3DPEHPK3PXP" and m._enc(enc, key) == enc
    assert (
        m._dec(enc, key) == "JBSWY3DPEHPK3PXP"
        and m._dec("JBSWY3DPEHPK3PXP", key) == "JBSWY3DPEHPK3PXP"
    )
