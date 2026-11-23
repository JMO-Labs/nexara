"""
@file test_relation_labels.py
@brief Inverse kinds and derived relative labels (with pronoun variants).
"""

import pytest

from app.services.relation_labels import derive, inverse


def test_inverse() -> None:
    assert inverse("parent") == "child"
    assert inverse("child") == "parent"
    assert inverse("spouse") == "spouse"
    assert inverse("friend") == "friend"


@pytest.mark.parametrize(
    ("path", "pronouns", "want"),
    [
        (["parent", "parent"], "she/her", "grandmother"),
        (["parent", "parent"], "he/him", "grandfather"),
        (["parent", "parent"], "they/them", "grandparent"),
        (["parent", "parent"], None, "grandparent"),
        (["parent", "sibling"], "she/her", "aunt"),
        (["parent", "sibling"], "he/him", "uncle"),
        (["parent", "sibling"], None, "aunt or uncle"),
        (["parent", "sibling", "child"], "he/him", "cousin"),
        (["sibling", "child"], "she/her", "niece"),
        (["sibling", "child"], "he", "nephew"),
        (["sibling", "child"], None, "niece or nephew"),
        (["spouse", "parent"], "she/her", "mother-in-law"),
        (["spouse", "parent"], None, "parent-in-law"),
        (["child", "child"], "she/her", "granddaughter"),
        (["child", "child"], None, "grandchild"),
        (["parent"], "she/her", "mother"),
        (["sibling"], None, "sibling"),
        (["parent", "parent", "parent", "friend"], None, "relative"),
        ([], None, "relative"),
    ],
)
def test_derive(path: list[str], pronouns: str | None, want: str) -> None:
    assert derive(path, pronouns) == want
