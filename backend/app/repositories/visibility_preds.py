"""
@file visibility_preds.py
@brief Reusable SQL predicates: can a viewer see a post / gallery / photo.
       Mirrors PostRepository.list_feed and GalleryService._can_view.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, exists, literal, or_, select
from sqlalchemy.orm import aliased

from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.models.moderation import UserBlock
from app.models.post import Post, PostMedia
from app.models.prompt import Prompt, PromptPost
from app.models.recipe import Recipe
from app.models.subgroup import SubgroupMember


def _in(col: Any, ids: Any) -> Any:
    """@brief ``col IN ids`` for a list (empty = false) or a subquery."""
    if isinstance(ids, list):
        return col.in_(ids) if ids else literal(False)
    return col.in_(ids)


def not_blocked(author_col: Any, viewer_id: uuid.UUID) -> Any:
    """@brief Author is not in a block relation with the viewer."""
    by_viewer = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
    of_viewer = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
    return and_(author_col.notin_(by_viewer), author_col.notin_(of_viewer))


def my_subgroup_ids(viewer_id: uuid.UUID) -> Any:
    """@brief Subquery of the viewer's subgroup ids (for ``*_visible`` predicates)."""
    return select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == viewer_id)


def post_visible(viewer_id: uuid.UUID, subgroup_ids: Any, community_id: uuid.UUID) -> Any:
    """
    @brief Live post the viewer may read (community, own private, or their group).
    @param subgroup_ids list of ids, or a subquery such as ``my_subgroup_ids``
    """
    # The group decides the audience: group posts are stored with
    # visibility "community" or "subgroup", so only "private" is special.
    return and_(
        Post.community_id == community_id,
        Post.deleted_at.is_(None),
        or_(
            and_(Post.visibility == "private", Post.author_id == viewer_id),
            and_(
                Post.visibility != "private",
                or_(Post.subgroup_id.is_(None), _in(Post.subgroup_id, subgroup_ids)),
            ),
        ),
        not_blocked(Post.author_id, viewer_id),
        answer_revealed(viewer_id),
    )


def answer_revealed(viewer_id: uuid.UUID) -> Any:
    """
    @brief Answers to an answer-to-reveal prompt (daily question) stay hidden
           until the viewer has answered that same prompt post themselves.
    """
    mine = aliased(Post)
    gated = exists().where(
        PromptPost.id == Post.reply_to_prompt_id,
        Prompt.id == PromptPost.prompt_id,
        Prompt.reveal_after_answer.is_(True),
        or_(Prompt.created_by.is_(None), Prompt.created_by != viewer_id),
    )
    answered = exists().where(
        mine.reply_to_prompt_id == Post.reply_to_prompt_id,
        mine.author_id == viewer_id,
        mine.deleted_at.is_(None),
    )
    return or_(Post.reply_to_prompt_id.is_(None), Post.author_id == viewer_id, ~gated, answered)


def gallery_visible(viewer_id: uuid.UUID, subgroup_ids: Any, community_id: uuid.UUID) -> Any:
    """@brief Gallery the viewer may open."""
    in_group = _in(Gallery.subgroup_id, subgroup_ids)
    collaborator = exists().where(
        GalleryCollaborator.gallery_id == Gallery.id, GalleryCollaborator.user_id == viewer_id
    )
    return and_(
        Gallery.community_id == community_id,
        or_(
            Gallery.visibility == "community",
            and_(Gallery.visibility == "subgroup", in_group),
            and_(Gallery.visibility == "private", or_(Gallery.owner_id == viewer_id, collaborator)),
        ),
    )


def media_visible(
    media_col: Any, viewer_id: uuid.UUID, subgroup_ids: Any, community_id: uuid.UUID
) -> Any:
    """@brief Photo appears in a post or gallery the viewer can see."""
    via_post = exists().where(
        PostMedia.media_id == media_col,
        Post.id == PostMedia.post_id,
        post_visible(viewer_id, subgroup_ids, community_id),
    )
    via_gallery = exists().where(
        GalleryItem.media_id == media_col,
        Gallery.id == GalleryItem.gallery_id,
        gallery_visible(viewer_id, subgroup_ids, community_id),
    )
    return or_(via_post, via_gallery)


def recipe_visible(viewer_id: uuid.UUID, subgroup_ids: Any, community_id: uuid.UUID) -> Any:
    """@brief Live recipe the viewer may read (own, community, or their group)."""
    return and_(
        Recipe.community_id == community_id,
        Recipe.deleted_at.is_(None),
        or_(
            Recipe.author_id == viewer_id,
            and_(
                not_blocked(Recipe.author_id, viewer_id),
                or_(
                    Recipe.visibility == "community",
                    and_(Recipe.visibility == "subgroup", _in(Recipe.subgroup_id, subgroup_ids)),
                ),
            ),
        ),
    )
