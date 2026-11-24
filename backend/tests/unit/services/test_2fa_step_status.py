"""
@file test_2fa_step_status.py
@brief /2fa/login re-checks suspension and memorialisation at step 2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pyotp
import pytest

from app.core.exceptions import AppError
from app.core.security import create_2fa_pending_token
from tests.unit.services.test_auth_security_fixes import _fake_redis
from tests.unit.services.test_auth_service import _make_service, _make_user


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [({"is_active": False}, "inactive"), ({"memorialized_at": datetime.now(UTC)}, "memorialized")],
)
async def test_suspended_during_pending_window_gets_no_tokens(overrides, reason):
    secret = pyotp.random_base32()
    svc = _make_service()
    user = _make_user(totp_enabled=True, totp_secret=secret, **overrides)
    svc._user_repo.get_by_id.return_value = user
    svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
    tok = create_2fa_pending_token(user.id, settings=svc._settings)
    with (
        patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()),
        patch("app.services.auth_service.log_failure", AsyncMock()) as fail,
        pytest.raises(AppError),
    ):
        await svc.verify_2fa_login(two_factor_token=tok, code=pyotp.TOTP(secret).now())
    svc._issue_tokens.assert_not_awaited()
    assert fail.await_args.args[4] == reason
