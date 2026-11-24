"""
@file test_presets.py
@brief SSO preset registry shape and URL rendering.
"""

import pytest

from app.services.oauth.presets import PRESETS


def test_nine_presets() -> None:
    assert set(PRESETS) == {
        "authentik", "keycloak", "authelia", "google", "microsoft",
        "gitlab", "github", "discord", "custom",
    }  # fmt: skip


@pytest.mark.parametrize("key", list(PRESETS))
def test_required_keys(key: str) -> None:
    p = PRESETS[key]
    assert p.kind in ("oidc", "oauth2") and p.scopes and p.help
    if p.kind == "oidc":
        assert p.discovery_url
    else:
        assert p.authorization_endpoint and p.token_endpoint and p.userinfo_endpoint


def test_render_urls() -> None:
    assert (
        PRESETS["authentik"].render_discovery_url(host="sso.x", slug="nx")
        == "https://sso.x/application/o/nx/.well-known/openid-configuration"
    )
    assert PRESETS["gitlab"].render_discovery_url().startswith("https://gitlab.com/")
    assert "/common/v2.0/" in (PRESETS["microsoft"].render_discovery_url() or "")


def test_groups_and_scopes() -> None:
    assert PRESETS["google"].claim_mapping.get("groups") is None
    assert "groups" in PRESETS["authelia"].scopes.split()
    assert PRESETS["github"].scopes == "read:user user:email read:org"
