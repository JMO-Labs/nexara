"""
@file test_passkeys.py
@brief PasskeyService: challenges, origin/replay/clone rejection, ownership, UV rules.
"""

from __future__ import annotations

import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from webauthn.helpers.exceptions import InvalidRegistrationResponse

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.core.security import create_2fa_pending_token
from app.models.passkey import Passkey
from app.services.auth.passkeys import PasskeyService

S = Settings(SECRET_KEY="pk-test", JWT_ALGORITHM="HS256", APP_BASE_URL="https://home.example:8443")
PR = "app.services.auth.passkeys."


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class FakeRedis:
    def __init__(self) -> None:
        self.d: dict[str, str] = {}

    async def set(self, k, v, ex=None):
        self.d[k] = v

    async def getdel(self, k):
        return self.d.pop(k, None)


@pytest.fixture
def redis():
    r = FakeRedis()
    with patch(PR + "get_pool", return_value=r):
        yield r


def _user(**kw):
    u = MagicMock()
    u.id, u.email, u.is_active, u.display_name = uuid.uuid4(), "a@b.c", True, "A"
    u.community_id = uuid.UUID(S.COMMUNITY_ID)
    u.memorialized_at = None
    for k, v in kw.items():
        setattr(u, k, v)
    return u


def _pk(user, sign=5):
    p = MagicMock(spec=Passkey)
    p.id, p.user_id, p.sign_count = uuid.uuid4(), user.id, sign
    p.credential_id, p.public_key = b"cred", b"pub"
    return p


def _svc():
    repo, users, tokens, audit = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    repo.session = MagicMock()
    repo.list_for_user.return_value = []
    repo.get_by_credential.return_value = None
    return (
        PasskeyService(repo, users, tokens, audit, S, uuid.UUID(S.COMMUNITY_ID), "1.2.3.4"),
        repo,
        users,
        audit,
    )


def _cred(challenge: bytes, raw_id: bytes = b"cred"):
    cdj = json.dumps({"challenge": b64(challenge), "origin": "x", "type": "t"}).encode()
    return {"id": b64(raw_id), "rawId": b64(raw_id), "response": {"clientDataJSON": b64(cdj)}}


def test_config_defaults_from_app_base_url():
    assert S.webauthn_rp_id == "home.example"
    assert S.webauthn_origins == ["https://home.example:8443"]
    s2 = Settings(
        WEBAUTHN_ORIGIN="http://localhost:8090, http://192.168.1.2:8090/", WEBAUTHN_RP_ID="x.y"
    )
    assert s2.webauthn_origins == ["http://localhost:8090", "http://192.168.1.2:8090"]
    assert s2.webauthn_rp_id == "x.y"


async def test_register_options_stores_challenge_and_excludes_existing(redis):
    svc, repo, _, _ = _svc()
    u = _user()
    repo.list_for_user.return_value = [_pk(u)]
    out = await svc.register_options(u)
    assert out["rp"]["id"] == "home.example"
    assert out["authenticatorSelection"]["residentKey"] == "preferred"
    assert len(out["excludeCredentials"]) == 1
    assert f"webauthn:chal:{out['challenge']}" in redis.d


async def test_register_wrong_origin_400(redis):
    svc, _, _, _ = _svc()
    u = _user()
    opts = await svc.register_options(u)
    cred = _cred(base64.urlsafe_b64decode(opts["challenge"] + "=="))
    with patch(
        PR + "verify_registration_response", side_effect=InvalidRegistrationResponse("origin")
    ) as v:
        with pytest.raises(AppError) as e:
            await svc.register_verify(u, cred, "n")
    assert e.value.status_code == 400
    assert v.call_args.kwargs["expected_origin"] == ["https://home.example:8443"]


async def test_register_replayed_challenge_400(redis):
    svc, repo, _, audit = _svc()
    u = _user()
    opts = await svc.register_options(u)
    cred = _cred(base64.urlsafe_b64decode(opts["challenge"] + "=="))
    ver = MagicMock(credential_id=b"c2", credential_public_key=b"k", sign_count=0)
    repo.add.side_effect = lambda p: p
    with patch(PR + "verify_registration_response", return_value=ver):
        await svc.register_verify(u, cred, "n")
        with pytest.raises(AppError) as e:
            await svc.register_verify(u, cred, "n")
    assert e.value.status_code == 400 and e.value.code == "challenge_expired"
    assert audit.append.await_args.kwargs["action"] == "passkey.added"


async def _login_setup(redis, sign_stored, sign_new, pending=False):
    svc, repo, users, _ = _svc()
    u = _user()
    pk = _pk(u, sign_stored)
    repo.get_by_credential.return_value = pk
    users.get_by_id.return_value = u
    opts = await svc.login_options(None)
    cred = _cred(base64.urlsafe_b64decode(opts["challenge"] + "=="))
    tok = create_2fa_pending_token(u.id, settings=S) if pending else None
    ver = MagicMock(new_sign_count=sign_new)
    return svc, repo, u, cred, tok, ver


async def test_sign_count_regression_rejected(redis):
    svc, repo, _, cred, _, ver = await _login_setup(redis, 5, 5)
    repo.touch.return_value = False
    with (
        patch(PR + "verify_authentication_response", return_value=ver),
        patch(PR + "log_failure", AsyncMock()),
        pytest.raises(AppError) as e,
    ):
        await svc.login_verify(cred, None, None)
    assert e.value.status_code == 400 and e.value.code == "passkey_cloned"
    repo.touch.assert_awaited_once()


async def test_passwordless_requires_uv_and_succeeds(redis):
    svc, repo, u, cred, _, ver = await _login_setup(redis, 5, 6)
    with (
        patch(PR + "verify_authentication_response", return_value=ver) as v,
        patch(PR + "log_success", AsyncMock()) as ok,
        patch(PR + "issue_tokens", AsyncMock(return_value={"access_token": "t"})),
    ):
        out = await svc.login_verify(cred, None, None)
    assert out == {"access_token": "t"}
    assert v.call_args.kwargs["require_user_verification"] is True
    repo.touch.assert_awaited_once()
    assert ok.await_args.args[3] == "passkey"


async def test_both_zero_counters_allowed_with_pending_token(redis):
    svc, repo, u, cred, tok, ver = await _login_setup(redis, 0, 0, pending=True)
    with (
        patch(PR + "verify_authentication_response", return_value=ver) as v,
        patch(PR + "reserve_attempt", AsyncMock(return_value=True)),
        patch(PR + "clear_user_attempts", AsyncMock()),
        patch(PR + "log_success", AsyncMock()),
        patch(PR + "issue_tokens", AsyncMock(return_value={"access_token": "t"})),
    ):
        await svc.login_verify(cred, tok, None)
    assert v.call_args.kwargs["require_user_verification"] is False


async def test_pending_token_for_other_user_rejected(redis):
    svc, _, _, cred, _, ver = await _login_setup(redis, 1, 2)
    other = create_2fa_pending_token(uuid.uuid4(), settings=S)
    with (
        patch(PR + "verify_authentication_response", return_value=ver),
        patch(PR + "reserve_attempt", AsyncMock(return_value=True)),
        patch(PR + "log_failure", AsyncMock()),
        pytest.raises(AppError) as e,
    ):
        await svc.login_verify(cred, other, None)
    assert e.value.status_code == 400


async def test_inactive_user_rejected(redis):
    svc, _, users, _ = _svc()
    u = _user(is_active=False)
    svc._repo.get_by_credential.return_value = _pk(u)
    users.get_by_id.return_value = u
    opts = await svc.login_options(None)
    cred = _cred(base64.urlsafe_b64decode(opts["challenge"] + "=="))
    with patch(PR + "log_failure", AsyncMock()), pytest.raises(AppError) as e:
        await svc.login_verify(cred, None, None)
    assert e.value.status_code == 400


async def test_delete_other_users_passkey_404():
    svc, repo, _, audit = _svc()
    repo.get_owned.return_value = None
    with pytest.raises(NotFoundError):
        await svc.remove(_user(), uuid.uuid4())
    audit.append.assert_not_awaited()


async def test_remove_audits():
    svc, repo, _, audit = _svc()
    u = _user()
    repo.get_owned.return_value = _pk(u)
    await svc.remove(u, uuid.uuid4())
    assert audit.append.await_args.kwargs["action"] == "passkey.removed"


async def test_duplicate_credential_race_409(redis):
    from sqlalchemy.exc import IntegrityError

    svc, repo, _, _ = _svc()
    u = _user()
    opts = await svc.register_options(u)
    cred = _cred(base64.urlsafe_b64decode(opts["challenge"] + "=="))
    repo.add.side_effect = IntegrityError("x", {}, Exception())
    ver = MagicMock(credential_id=b"c2", credential_public_key=b"k", sign_count=0)
    with patch(PR + "verify_registration_response", return_value=ver):
        with pytest.raises(AppError) as e:
            await svc.register_verify(u, cred, "n")
    assert e.value.status_code == 409 and e.value.code == "passkey_exists"
