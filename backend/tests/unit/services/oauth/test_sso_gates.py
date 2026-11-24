"""
@file test_sso_gates.py
@brief evaluate_gates: the one gate sequence shared by UserProvisioner and test login.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.services.oauth import sso_rules, sso_test_login
from app.services.oauth.sso_rules import GateDecision, evaluate_gates
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
from tests.unit.services.oauth.helpers import sso_provider


def _auth(email: str | None = "a@x.org", verified: bool = True, groups=None):
    return OAuthAuthResult(sub="s", email=email, email_verified=verified, groups=groups)


def _user(active: bool = True, verified: bool = True) -> MagicMock:
    u = MagicMock(spec=User)
    u.is_active, u.email_verified = active, verified
    return u


LINK = MagicMock(spec=UserOAuthLink)


@pytest.mark.parametrize(
    ("kw", "auth", "expected"),
    [
        (
            {"provider": sso_provider(allowed_domains=["corp.org"])},
            _auth(),
            "sso_domain_not_allowed",
        ),
        (
            {"provider": sso_provider(required_group="fam")},
            _auth(groups=["x"]),
            "sso_group_required",
        ),
        ({"link": LINK, "linked_user": None}, _auth(), "sso_account_disabled"),
        ({"link": LINK, "linked_user": _user(active=False)}, _auth(), "sso_account_disabled"),
        ({}, _auth(verified=False), "sso_email_unverified"),
        ({"email_user": _user(active=False)}, _auth(), "sso_account_disabled"),
        ({"email_user": _user(verified=False)}, _auth(), "sso_email_unverified_local"),
        ({"provider": sso_provider(auto_create_users=False)}, _auth(), "sso_no_account"),
    ],
)
def test_refusals(kw, auth, expected):
    provider = kw.pop("provider", sso_provider())
    assert evaluate_gates(provider, auth, **kw) == GateDecision(code=expected)


def test_gate_checked_before_link():
    """A linked user failing the domain gate is refused (not signed in)."""
    p = sso_provider(allowed_domains=["corp.org"])
    d = evaluate_gates(p, _auth(), link=LINK, linked_user=_user())
    assert d.code == "sso_domain_not_allowed"


def test_unverified_email_never_satisfies_domain_gate():
    p = sso_provider(allowed_domains=["x.org"])
    assert evaluate_gates(p, _auth(verified=False)).code == "sso_domain_not_allowed"


@pytest.mark.parametrize(
    ("kw", "action"),
    [
        ({"link": LINK, "linked_user": _user()}, "sign_in"),
        ({"email_user": _user()}, "link"),
        ({}, "create"),
    ],
)
def test_allowed_actions(kw, action):
    assert evaluate_gates(sso_provider(), _auth(), **kw) == GateDecision(action=action)


async def test_provisioner_uses_evaluate_gates():
    prov = UserProvisioner(AsyncMock(), uuid.uuid4())
    prov._link_repo = AsyncMock()
    prov._link_repo.find_by_provider_and_sub.return_value = None
    prov._user_repo = AsyncMock()
    prov._user_repo.find_by_email.return_value = None
    spy = MagicMock(return_value=GateDecision(code="sso_no_account"))
    with patch("app.services.oauth.user_provisioner.evaluate_gates", spy):
        with pytest.raises(Exception, match="sso_no_account"):
            await prov.provision_user(_auth(), sso_provider(), "member")
    spy.assert_called_once()


async def test_test_login_preview_uses_evaluate_gates():
    links, users = AsyncMock(), AsyncMock()
    links.find_by_provider_and_sub.return_value = None
    users.find_by_email.return_value = None
    spy = MagicMock(wraps=sso_rules.evaluate_gates)
    with (
        patch.object(sso_test_login, "UserOAuthLinkRepository", return_value=links),
        patch.object(sso_test_login, "UserRepository", return_value=users),
        patch.object(sso_test_login, "evaluate_gates", spy),
    ):
        out = await sso_test_login.preview_outcome(AsyncMock(), sso_provider(), _auth())
    spy.assert_called_once()
    assert out == {"allowed": True, "action": "create", "code": None}
