"""
@file test_branding_css.py
@brief Unit tests for the custom CSS sanitizer.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.services.branding.css import sanitize_css

SAFE = (
    "a:hover{color:#fff;background:rgb(0,0,0)}\n"
    "@media (max-width:600px){.x::before{content:'a';display:flex}}\n"
    "@keyframes k{from{opacity:0}to{opacity:1}}"
)


def test_valid_css_unchanged() -> None:
    assert sanitize_css(SAFE) == SAFE


def test_strips_import() -> None:
    out = sanitize_css("@import url(http://evil/x.css);body{color:red}")
    assert "@import" not in out
    assert "body{color:red}" in out


@pytest.mark.parametrize("scheme", ["javascript", "data", "vbscript", "JaVaScRiPt"])
def test_strips_dangerous_url(scheme: str) -> None:
    out = sanitize_css(f"a{{background:url('{scheme}:alert(1)')}}")
    assert scheme.lower() not in out.lower()


def test_keeps_safe_url() -> None:
    css = "a{background:url(https://example.com/a.png)}"
    assert sanitize_css(css) == css


def test_strips_expression() -> None:
    assert "expression" not in sanitize_css("a{width:expression(alert(1))}")


def test_strips_behavior() -> None:
    out = sanitize_css("a{behavior:url(x.htc);color:red}")
    assert "behavior" not in out
    assert "color:red" in out


def test_strips_script_protocols() -> None:
    out = sanitize_css("a{x:vbscript:foo;y:jscript:bar}")
    assert "vbscript:" not in out
    assert "jscript:" not in out


def test_nested_payload_does_not_reassemble() -> None:
    assert "@import" not in sanitize_css("@imp@import x;ort url(y);")


def test_comment_split_payload() -> None:
    assert "expression" not in sanitize_css("a{width:expr/**/ession(alert(1))}")


def test_strips_style_close_tag() -> None:
    assert "</style" not in sanitize_css("a{}</style><script>x</script>").lower()


def test_rejects_too_large() -> None:
    with pytest.raises(AppError) as exc:
        sanitize_css("a{}" * 5000)
    assert exc.value.code == "css_too_large"
    assert exc.value.status_code == 400


async def test_service_sanitizes_before_save() -> None:
    import uuid
    from unittest.mock import AsyncMock

    from app.repositories.branding_repo import BrandingRepository
    from app.schemas.branding import BrandingUpdate
    from app.services.branding_service import BrandingService

    repo = AsyncMock(spec=BrandingRepository)
    repo.upsert.return_value = SimpleNamespace(
        community_name="C", tagline="t", color_primary="#000000", color_primary_dark="#111111"
    )
    svc = BrandingService(repo=repo)
    await svc.update_branding(
        user_id=uuid.uuid4(),
        data=BrandingUpdate(
            custom_css="@import 'x';a{color:red;padding:1px;margin:1px;width:1px}",
            custom_css_enabled=True,
        ),
    )
    saved = repo.upsert.call_args.args[1]
    assert "@import" not in saved["custom_css"]


async def test_service_rejects_when_too_much_removed() -> None:
    import uuid
    from unittest.mock import AsyncMock

    from app.repositories.branding_repo import BrandingRepository
    from app.schemas.branding import BrandingUpdate
    from app.services.branding_service import BrandingService

    repo = AsyncMock(spec=BrandingRepository)
    svc = BrandingService(repo=repo)
    with pytest.raises(AppError) as exc:
        await svc.update_branding(
            user_id=uuid.uuid4(),
            data=BrandingUpdate(
                custom_css="@import url(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa);a{}",
                custom_css_enabled=True,
            ),
        )
    assert exc.value.code == "css_invalid"
    assert exc.value.status_code == 400
    repo.upsert.assert_not_called()


@pytest.mark.parametrize("enabled", [None, False])
async def test_service_sanitizes_when_toggle_not_true(enabled: bool | None) -> None:
    import uuid
    from unittest.mock import AsyncMock

    from app.repositories.branding_repo import BrandingRepository
    from app.schemas.branding import BrandingUpdate
    from app.services.branding_service import BrandingService

    repo = AsyncMock(spec=BrandingRepository)
    repo.upsert.return_value = SimpleNamespace(
        community_name="C", tagline="t", color_primary="#000000", color_primary_dark="#111111"
    )
    svc = BrandingService(repo=repo)
    await svc.update_branding(
        user_id=uuid.uuid4(),
        data=BrandingUpdate(
            custom_css="@import 'x';a{color:red;padding:1px;margin:1px;width:1px}",
            custom_css_enabled=enabled,
        ),
    )
    saved = repo.upsert.call_args.args[1]
    assert "@import" not in saved["custom_css"]


@pytest.mark.parametrize("css", ['@import"https://evil/x.css";a{}', "@import'x.css';a{}"])
def test_strips_import_without_whitespace(css: str) -> None:
    assert "@import" not in sanitize_css(css).lower()


@pytest.mark.parametrize(
    "css",
    ["@\\69mport url(x);a{}", 'a{b:url("java\\73 cript:x")}', "a{b:\\65xpression(1)}"],
)
def test_rejects_css_escapes(css: str) -> None:
    with pytest.raises(AppError) as exc:
        sanitize_css(css)
    assert exc.value.code == "css_invalid"
    assert exc.value.status_code == 400
