"""
@file
@brief Tests for plugin token generation and the rate-limit key.
"""

from types import SimpleNamespace

from starlette.datastructures import Headers

from app.core.rate_limit import rate_limit_key
from app.plugins.tokens import hash_token, new_token


def test_new_token_shape_and_hash() -> None:
    plain, h = new_token()
    assert plain.startswith("nxp_") and len(plain) > 40
    assert h == hash_token(plain) and len(h) == 64
    assert new_token()[0] != plain


def _req(headers: dict[str, str], token_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        headers=Headers(headers),
        client=SimpleNamespace(host="10.0.0.9"),
        state=SimpleNamespace(plugin_token_id=token_id),
    )


def test_rate_key_plugin_token_id() -> None:
    assert rate_limit_key(_req({}, "abc")) == "plugin:abc"


def test_rate_key_plugin_header_not_ip() -> None:
    k = rate_limit_key(_req({"authorization": "Bearer nxp_secret"}))
    assert k.startswith("plugin:") and "nxp_secret" not in k


def test_rate_key_human_is_ip() -> None:
    assert rate_limit_key(_req({"authorization": "Bearer eyJ"})) == "10.0.0.9"
