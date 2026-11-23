"""
@file relation_labels.py
@brief Pure helpers: inverse of a stored relation kind and derived
       relative labels (grandparent, aunt, cousin ...) from a kind path.
"""

from __future__ import annotations

_INVERSE = {"parent": "child", "child": "parent"}

# path -> (female, male, neutral)
_WORDS: dict[tuple[str, ...], tuple[str, str, str]] = {
    ("parent",): ("mother", "father", "parent"),
    ("child",): ("daughter", "son", "child"),
    ("sibling",): ("sister", "brother", "sibling"),
    ("spouse",): ("wife", "husband", "spouse"),
    ("partner",): ("partner", "partner", "partner"),
    ("friend",): ("friend", "friend", "friend"),
    ("parent", "parent"): ("grandmother", "grandfather", "grandparent"),
    ("child", "child"): ("granddaughter", "grandson", "grandchild"),
    ("parent", "sibling"): ("aunt", "uncle", "aunt or uncle"),
    ("sibling", "child"): ("niece", "nephew", "niece or nephew"),
    ("parent", "sibling", "child"): ("cousin", "cousin", "cousin"),
    ("spouse", "parent"): ("mother-in-law", "father-in-law", "parent-in-law"),
}


def inverse(kind: str) -> str:
    """
    @brief The kind seen from the other side (parent <-> child, rest symmetric).
    @param kind Stored relation kind.
    @return Inverse kind.
    """
    return _INVERSE.get(kind, kind)


def _gender(pronouns: str | None) -> int:
    """@brief 0 = female word, 1 = male word, 2 = neutral."""
    first = (pronouns or "").strip().lower().split("/")[0]
    if first in ("she", "her"):
        return 0
    return 1 if first in ("he", "him") else 2


def derive(path: list[str], pronouns: str | None) -> str:
    """
    @brief Label for the person at the end of a kind path from the viewer.
    @param path Base kinds from the viewer outward, e.g. ["parent", "parent"].
    @param pronouns The labelled person's pronouns (picks the word).
    @return E.g. "grandmother"; "relative" for an unknown path.
    """
    words = _WORDS.get(tuple(path))
    return "relative" if words is None else words[_gender(pronouns)]
