"""
@file visibility_preds.py
@brief Reusable SQL predicates: can a viewer see a post / gallery / photo.
       Mirrors PostRepository.list_feed and GalleryService._can_view.
       NSFW content is adults-only on every predicate here.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Date, and_, case, cast, exists, extract, func, literal, or_, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import aliased

from app.models.community import Community
from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.post import Post, PostMedia
from app.models.prompt import Prompt, PromptPost
from app.models.recipe import Recipe
from app.models.subgroup import SubgroupMember
from app.models.user import User


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


def viewer_is_adult(viewer_id: uuid.UUID | None) -> Any:
    """
    @brief SQL mirror of ``age_service.is_adult`` for one viewer (unknown = not adult).
           Admin-set group wins; else birthday >= 18 (UTC date) unless the
           community requires approval for adults. No viewer = not adult.
    """
    if viewer_id is None:
        return literal(False)
    # Aliases: never auto-correlate to a users/communities row of the outer query.
    u, c = aliased(User), aliased(Community)
    return exists().where(u.id == viewer_id, c.id == u.community_id, adult_cond(u, c))


def adult_cond(u: Any, c: Any) -> Any:
    """
    @brief Row-level adult test for user ``u`` joined to its community ``c``
           (mirror of ``age_service.effective_age_group == "adult"``).
    """
    today = cast(func.timezone("UTC", func.now()), Date)
    by_birthday = and_(
        u.age_group.is_(None),
        u.birthday.is_not(None),
        extract("year", func.age(today, u.birthday)) >= 18,
        c.adult_requires_approval.is_(False),
    )
    return or_(u.age_group == "adult", by_birthday)


def _adult(viewer_id: uuid.UUID | None, viewer_adult: bool | None) -> Any:
    """@brief Literal for a precomputed bool, else the SQL derivation."""
    if viewer_adult is None:
        return viewer_is_adult(viewer_id)
    return literal(bool(viewer_adult))


def nsfw_allowed(viewer_adult: Any, flag: Any = None) -> Any:
    """
    @brief Content is not NSFW, or the viewer is an adult.
    @param viewer_adult bool or SQL boolean (see ``viewer_is_adult``)
    @param flag NSFW column to test (default ``Post.is_nsfw``)
    """
    adult = literal(viewer_adult) if isinstance(viewer_adult, bool) else viewer_adult
    return or_((Post.is_nsfw if flag is None else flag).is_(False), adult)


def media_is_nsfw(media_col: Any) -> Any:
    """
    @brief Photo is NSFW itself, attached to an NSFW post or in an NSFW album, or
           reached by a moderator container flag (``media_nsfw_sources``).
    """
    from app.models.media_nsfw_source import MediaNsfwSource

    src = aliased(MediaNsfwSource)
    pm, p = aliased(PostMedia), aliased(Post)
    gi, g = aliased(GalleryItem), aliased(Gallery)
    in_post = exists().where(pm.media_id == media_col, p.id == pm.post_id, p.is_nsfw.is_(True))
    in_album = exists().where(gi.media_id == media_col, g.id == gi.gallery_id, g.is_nsfw.is_(True))
    m = aliased(Media)
    flagged = exists().where(m.id == media_col, m.is_nsfw.is_(True))
    sourced = exists().where(src.media_id == media_col)
    return or_(flagged, in_post, in_album, sourced)


def media_nsfw_ok(
    media_col: Any, viewer_id: uuid.UUID | None, viewer_adult: bool | None = None
) -> Any:
    """@brief Photo is safe for everyone, or the viewer is an adult."""
    return or_(~media_is_nsfw(media_col), _adult(viewer_id, viewer_adult))


_UUID_RE = "^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$"


def payload_uuid(payload_col: Any, key: str) -> Any:
    """@brief ``payload->>key`` as a UUID, NULL when absent or malformed."""
    txt = payload_col[key].astext
    return case((txt.op("~")(_UUID_RE), cast(txt, PG_UUID(as_uuid=True))), else_=None)


def target_is_nsfw(post_id: Any, gallery_id: Any, media_id: Any) -> Any:
    """@brief Any of the referenced post / album / photo is NSFW (NULL refs ignored)."""
    p, g = aliased(Post), aliased(Gallery)
    return or_(
        exists().where(p.id == post_id, p.is_nsfw.is_(True)),
        exists().where(g.id == gallery_id, g.is_nsfw.is_(True)),
        media_is_nsfw(media_id),
    )


def payload_nsfw_ok(payload_col: Any, viewer_id: uuid.UUID) -> Any:
    """@brief Notification payload points at nothing NSFW, or the viewer is an adult."""
    nsfw = target_is_nsfw(
        payload_uuid(payload_col, "post_id"),
        payload_uuid(payload_col, "gallery_id"),
        payload_uuid(payload_col, "media_id"),
    )
    return or_(~nsfw, viewer_is_adult(viewer_id))


def post_visible(
    viewer_id: uuid.UUID,
    subgroup_ids: Any,
    community_id: uuid.UUID,
    viewer_adult: bool | None = None,
) -> Any:
    """
    @brief Live post the viewer may read (community, own private, or their group).
           NSFW posts are visible to adults only, the author included.
    @param subgroup_ids list of ids, or a subquery such as ``my_subgroup_ids``
    @param viewer_adult precomputed ``age_service.is_adult``; None derives it in SQL
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
        nsfw_allowed(_adult(viewer_id, viewer_adult)),
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


def outside_daily_question() -> Any:
    """
    @brief Not the daily question's own post nor an answer to it; the feed
           shows those inside the question card instead of repeating them.
    """
    daily = (
        select(PromptPost.id, PromptPost.post_id)
        .join(Prompt, Prompt.id == PromptPost.prompt_id)
        .where(Prompt.prompt_type == "daily_question")
        .subquery()
    )
    return and_(
        or_(Post.reply_to_prompt_id.is_(None), Post.reply_to_prompt_id.notin_(select(daily.c.id))),
        Post.id.notin_(select(daily.c.post_id)),
    )


def gallery_visible(
    viewer_id: uuid.UUID,
    subgroup_ids: Any,
    community_id: uuid.UUID,
    viewer_adult: bool | None = None,
) -> Any:
    """@brief Gallery the viewer may open (NSFW albums: adults only)."""
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
        nsfw_allowed(_adult(viewer_id, viewer_adult), Gallery.is_nsfw),
    )


def media_visible(
    media_col: Any, viewer_id: uuid.UUID, subgroup_ids: Any, community_id: uuid.UUID
) -> Any:
    """@brief Photo appears in a post or gallery the viewer can see, and is NSFW-safe."""
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
    return and_(or_(via_post, via_gallery), media_nsfw_ok(media_col, viewer_id))


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
