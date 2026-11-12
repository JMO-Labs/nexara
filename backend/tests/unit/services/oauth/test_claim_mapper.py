"""
@file test_claim_mapper.py
@brief Tests for claim_mapping driven claim extraction.
"""

from __future__ import annotations

from app.services.oauth.claim_mapper import DEFAULT_MAPPING, map_claims


def test_default_mapping():
    r = map_claims({"sub": "1", "email": "a@b.c", "name": "A", "groups": ["x"]}, None)
    assert (r.sub, r.email, r.display_name, r.groups) == ("1", "a@b.c", "A", ["x"])


def test_custom_mapping_overrides_defaults():
    mapping = {"email": "mail", "name": "preferred_username", "groups": "roles"}
    r = map_claims(
        {"sub": "9", "mail": "m@x.y", "preferred_username": "mo", "roles": ["r1", "r2"]},
        mapping,
    )
    assert r.email == "m@x.y"
    assert r.display_name == "mo"
    assert r.groups == ["r1", "r2"]


def test_nested_dotted_path():
    r = map_claims({"sub": "1", "realm_access": {"roles": ["a"]}}, {"groups": "realm_access.roles"})
    assert r.groups == ["a"]


def test_missing_and_string_group():
    r = map_claims({"sub": "1", "groups": "solo"}, {})
    assert r.groups == ["solo"] and r.email is None


def test_default_mapping_keys():
    assert {"email", "name", "groups"} <= set(DEFAULT_MAPPING)
