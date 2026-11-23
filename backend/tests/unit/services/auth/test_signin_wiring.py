"""
@file test_signin_wiring.py
@brief AuthService records sign-in events on password, magic link and SSO paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from tests.unit.services.test_auth_security_fixes import _make_service, _make_user

REC = "app.services.auth.signin_log.record_signin_safe"


async def test_wrong_password_records_bad_password_and_commits():
    svc = _make_service()
    svc._user_repo.find_by_email.return_value = _make_user(password_hash="x")
    svc._session.commit = AsyncMock()
    with (
        patch(REC, AsyncMock(return_value=object())) as rec,
        patch("app.services.auth_service.verify_password", return_value=False),
        patch.object(svc, "_assert_password_auth_allowed", AsyncMock()),
        pytest.raises(AuthenticationError),
    ):
        await svc.login(email="a@b.c", password="nope")
    kw = rec.await_args.kwargs
    assert (kw["method"], kw["success"], kw["reason"]) == ("password", False, "bad_password")
    assert "password" not in kw
    svc._session.commit.assert_awaited_once()


async def test_unknown_email_records_null_user():
    svc = _make_service()
    svc._user_repo.find_by_email.return_value = None
    with (
        patch(REC, AsyncMock(return_value=None)) as rec,
        patch.object(svc, "_assert_password_auth_allowed", AsyncMock()),
        pytest.raises(AuthenticationError),
    ):
        await svc.login(email="Nobody@b.c", password="nope")
    kw = rec.await_args.kwargs
    assert kw["user_id"] is None
    assert kw["reason"] == "unknown_email"


async def test_login_sso_records_sso_success():
    svc = _make_service()
    svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
    with patch(REC, AsyncMock()) as rec:
        out = await svc.login_sso(_make_user(), request=None)
    assert out == {"access_token": "a"}
    assert rec.await_args.kwargs["method"] == "sso"
    assert rec.await_args.kwargs["success"] is True


async def test_magic_link_failure_recorded():
    svc = _make_service()
    with (
        patch(REC, AsyncMock(return_value=None)) as rec,
        patch.object(svc, "_assert_password_auth_allowed", AsyncMock()),
        patch(
            "app.services.auth_service._verify_magic_link_impl",
            AsyncMock(side_effect=AuthenticationError(message="bad")),
        ),
        pytest.raises(AuthenticationError),
    ):
        await svc.verify_magic_link("tok")
    assert rec.await_args.kwargs["method"] == "magic_link"
    assert rec.await_args.kwargs["success"] is False
