"""
@file
@brief Tests for the plugin manifest parser and field validation.
"""

import pytest

from app.core.exceptions import AppError
from app.plugins.manifest import (
    core_version,
    is_compatible,
    parse_manifest,
    validate_values,
    with_defaults,
)

TOML = """
[plugin]
id = "io.jmolabs.sassybot"
name = "Sassybot"
version = "1.0.0"
description = "A bot."
author = "JMO Labs"
license = "MIT"
homepage = "https://example.com"
min_core_version = "0.1.0"
runtime = "node"
entrypoint = "dist/index.js"
icon = "assets/icon.png"

[bot]
display_name = "Sassybot"
username = "sassybot"
avatar = "assets/avatar.png"

[permissions]
scopes = ["posts:read", "comments:write"]
events = ["post.created", "mention"]
egress = ["api.anthropic.com"]

[settings.daily_cap]
type = "number"
label = "Cap"
min = 0
max = 500
default = 30

[settings.claude_token]
type = "secret"
label = "Token"

[user_prefs.roast_level]
type = "select"
label = "Roast me"
options = ["off", "mild", "full"]
default = "off"

[composer_flags.roast_me]
type = "boolean"
label = "Roast"
"""


def _bad(old: str, new: str) -> str:
    assert old in TOML
    return TOML.replace(old, new)


def test_parses_spec_example() -> None:
    m = parse_manifest(TOML)
    assert m.id == "io.jmolabs.sassybot"
    assert m.bot_username == "sassybot"
    assert m.icon == "assets/icon.png"
    assert m.bot_avatar == "assets/avatar.png"
    assert m.user_prefs["roast_level"].options == ["off", "mild", "full"]
    assert m.settings["claude_token"].type == "secret"


@pytest.mark.parametrize(
    "old,new",
    [
        ('"posts:read", "comments:write"', '"db:write"'),
        ('"post.created", "mention"', '"nope"'),
        ('id = "io.jmolabs.sassybot"', 'id = "Bad_ID"'),
        ('version = "1.0.0"', 'version = "1.x"'),
        ('type = "select"', 'type = "secret"'),
    ],
)
def test_rejects_bad_manifest(old: str, new: str) -> None:
    with pytest.raises(AppError) as e:
        parse_manifest(_bad(old, new))
    assert e.value.code == "invalid_manifest"
    assert e.value.status_code == 422
    assert e.value.details["errors"]


def test_rejects_invalid_toml() -> None:
    with pytest.raises(AppError) as e:
        parse_manifest("[[")
    assert e.value.code == "invalid_manifest"


def test_validate_values() -> None:
    m = parse_manifest(TOML)
    p = m.user_prefs
    assert validate_values(p, {"roast_level": "mild"}) == {"roast_level": "mild"}
    for fields, vals in [
        (p, {"roast_level": "x"}),
        (p, {"nope": 1}),
        (m.settings, {"daily_cap": 501}),
        (m.settings, {"daily_cap": True}),
        (m.composer_flags, {"roast_me": "yes"}),
    ]:
        with pytest.raises(AppError) as e:
            validate_values(fields, vals)
        assert e.value.code == "invalid_plugin_value"
        assert e.value.status_code == 422


def test_with_defaults_fills_missing() -> None:
    m = parse_manifest(TOML)
    assert with_defaults(m.user_prefs, {}) == {"roast_level": "off"}


def test_compat() -> None:
    m = parse_manifest(TOML)
    assert is_compatible(m)
    assert core_version()
    m2 = parse_manifest(_bad('min_core_version = "0.1.0"', 'min_core_version = "999.0.0"'))
    assert not is_compatible(m2)
