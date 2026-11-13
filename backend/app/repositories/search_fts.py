"""
@file search_fts.py
@brief Shared full-text-search expression helpers.

Split from search_repo.py.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, func
from sqlalchemy.sql.expression import ColumnElement

from app.models.post import Comment, Post


def _websearch_tsquery() -> ColumnElement[Any]:
    """
    @brief Build a websearch_to_tsquery expression bound to parameter 'q'.

    websearch_to_tsquery handles raw user input directly -- including
    quoted phrases, stop words, hyphens, and special characters -- without
    requiring manual sanitization.
    """
    return func.websearch_to_tsquery("english", bindparam("q"))


def _prefix_tsquery() -> ColumnElement[Any]:
    """
    @brief Build a to_tsquery expression bound to parameter 'q_prefix'.

    Uses the :* operator on each term so that partial words match stemmed
    lexemes in the GIN index (e.g. "app:*" matches "appl" from "apple").
    """
    return func.to_tsquery("english", bindparam("q_prefix"))


def _fts_expressions(fts_col: Any, prefix_query: str | None) -> tuple[Any, Any, dict[str, str]]:
    """
    @brief Build FTS match expression, rank expression, and bind-param dict.

    When a non-empty *prefix_query* is supplied the WHERE clause uses OR
    to match either the websearch (stemmed full-word) or prefix query, and
    ranking uses GREATEST of both strategies.

    @param fts_col       The TSVECTOR column to match against.
    @param prefix_query  Prefix tsquery string or empty/None.
    @return Tuple of (match_expr, rank_expr, extra_params).
    """
    tsq_ws = _websearch_tsquery()

    if prefix_query:
        tsq_pf = _prefix_tsquery()
        match = fts_col.op("@@")(tsq_ws) | fts_col.op("@@")(tsq_pf)
        rank = func.greatest(
            func.ts_rank(fts_col, tsq_ws),
            func.ts_rank(fts_col, tsq_pf),
        )
        return match, rank, {"q_prefix": prefix_query}

    match = fts_col.op("@@")(tsq_ws)
    rank = func.ts_rank(fts_col, tsq_ws)
    return match, rank, {}


def _exclude_nsfw_comments(stmt: Any) -> Any:
    """@brief Join the parent post and drop comments on NSFW posts."""
    return stmt.join(Post, Post.id == Comment.post_id).where(Post.is_nsfw.is_(False))
