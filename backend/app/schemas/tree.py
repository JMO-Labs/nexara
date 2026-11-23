"""
@file tree.py
@brief Response models for the family tree and group relationship tree.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

NodeKind = Literal["user", "household", "private"]
EdgeKind = Literal["parent", "spouse", "partner", "sibling", "friend", "other", "via_family"]


class TreeNode(BaseModel):
    """
    @brief One person. ``private`` nodes carry no name, avatar, link or
           dates; their id is a throwaway ``p:<n>``.
    """

    id: str
    name: str
    avatar_url: str | None = None
    kind: NodeKind
    memorial: bool = False
    link: str | None = None
    born: str | None = None
    died: str | None = None


class TreeEdge(BaseModel):
    """@brief ``a`` -> ``b``; for ``parent``, a is the parent of b."""

    a: str
    b: str
    kind: EdgeKind


class TreeOut(BaseModel):
    """@brief A tree slice."""

    nodes: list[TreeNode]
    edges: list[TreeEdge]
    root: str | None = None
    truncated: bool = False
