"""
@file relation_service.py
@brief Relations between members (request -> confirm) and to the
       requester's own household members (auto-confirmed). Lists honor the
       owner's "relations" field visibility and blocks; people the viewer
       can't see are left out.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.features import require_feature
from app.core.i18n import _
from app.models.relation import Relation
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.schemas.relation import RelationOut, RelationPerson
from app.services.notification_service import NotificationService
from app.services.profiles.visibility import allowed, effective_levels
from app.services.relation_labels import derive, inverse


class RelationService:
    """@brief Business rules for relations."""

    def __init__(
        self,
        repo: RelationRepository,
        profiles: ProfileRepository,
        household: HouseholdRepository,
        communities: CommunityRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._profiles = profiles
        self._household = household
        self._communities = communities
        self._notify = notifications
        self._cid = community_id

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._cid)
        if community is not None:
            require_feature(community, "relations")

    async def request(
        self,
        actor: User,
        *,
        to_user_id: uuid.UUID | None = None,
        to_member_id: uuid.UUID | None = None,
        kind: str,
        label: str | None = None,
    ) -> Relation:
        """
        @brief Ask to link a person ("Ruth is my parent").
        @param actor Requesting user.
        @param to_user_id Another member (pending until they confirm).
        @param to_member_id One of the actor's own household members (auto-confirmed).
        @param kind What the other person is to the actor.
        @param label Free text for kind ``other`` (max 40).
        @return The stored relation.
        @throws NotFoundError unknown, blocked or not-owned target.
        @throws ValidationError self or memorialized target.
        @throws ConflictError the pair is already linked.
        """
        await self._require_feature()
        stored = inverse(kind)
        if to_member_id is not None:
            member = await self._household.get(to_member_id, self._cid)
            if member is None or member.owner_id != actor.id or member.deleted_at is not None:
                raise NotFoundError(message=_("Person not found"))
            if await self._repo.pair_exists(self._cid, actor.id, member_id=member.id):
                raise ConflictError(message=_("You're already linked"))
            rel = await self._repo.create(
                community_id=self._cid,
                from_user_id=actor.id,
                to_household_member_id=member.id,
                kind=stored,
                label=label,
                status="confirmed",
                created_by=actor.id,
                confirmed_at=datetime.now(UTC),
            )
        else:
            assert to_user_id is not None
            if to_user_id == actor.id:
                raise ValidationError(message=_("You can't link yourself"))
            found = await self._repo.users_visible([to_user_id], actor.id, self._cid)
            target = found.get(to_user_id)
            if target is None:
                raise NotFoundError(message=_("Person not found"))
            if target.memorialized_at is not None:
                raise ValidationError(message=_("Ask an admin to link a remembered person"))
            if await self._repo.pair_exists(self._cid, actor.id, user_id=target.id):
                raise ConflictError(message=_("You're already linked"))
            rel = await self._repo.create(
                community_id=self._cid,
                from_user_id=actor.id,
                to_user_id=target.id,
                kind=stored,
                label=label,
                status="pending",
                created_by=actor.id,
            )
            if rel is not None:
                await self._notify_request(actor, target, rel, kind, label)
        if rel is None:
            raise ConflictError(message=_("You're already linked"))
        return rel

    async def _notify_request(
        self, actor: User, target: User, rel: Relation, kind: str, label: str | None
    ) -> None:
        """@brief Tell the target who asked and how they're described."""
        role = label if kind == "other" and label else derive([kind], target.pronouns)
        await self._notify.notify(
            target.id,
            "relation_request",
            {
                "message": _("%(name)s says you are their %(role)s")
                % {"name": actor.display_name, "role": role},
                "link": f"/app/u/{actor.username}",
                "relation_id": str(rel.id),
                "requester_name": actor.display_name,
            },
            actor.id,
        )

    async def _party(self, relation_id: uuid.UUID, actor: User) -> Relation:
        """@brief The relation if the actor is a party; anyone else sees not found."""
        rel = await self._repo.get(relation_id, self._cid)
        if rel is None or actor.id not in (rel.from_user_id, rel.to_user_id):
            raise NotFoundError(message=_("Request not found"))
        other = rel.to_user_id if actor.id == rel.from_user_id else rel.from_user_id
        if other and await self._profiles.blocked_either_way(actor.id, other):
            raise NotFoundError(message=_("Request not found"))
        return rel

    async def confirm(self, relation_id: uuid.UUID, actor: User) -> Relation:
        """
        @brief Accept a request. Only the person it was sent to can.
        @throws NotFoundError for strangers; AuthorizationError for the sender.
        """
        await self._require_feature()
        rel = await self._party(relation_id, actor)
        if rel.to_user_id != actor.id:
            raise AuthorizationError(message=_("Only the other person can confirm"))
        if rel.status == "confirmed":
            return rel
        return await self._repo.confirm(rel, datetime.now(UTC))

    async def remove(self, relation_id: uuid.UUID, actor: User) -> None:
        """@brief Decline, cancel or remove. Either side or an admin."""
        await self._require_feature()
        rel = await self._repo.get(relation_id, self._cid)
        if rel is None:
            raise NotFoundError(message=_("Request not found"))
        if actor.role == "admin" and actor.id not in (rel.from_user_id, rel.to_user_id):
            pass
        else:
            await self._party(relation_id, actor)
        await self._repo.delete(rel)

    async def _persons(
        self, rels: list[Relation], subject_id: uuid.UUID, viewer_id: uuid.UUID
    ) -> list[RelationOut]:
        """@brief Build outputs for ``subject_id``, dropping people the viewer can't see."""
        other_user = {
            (r.to_user_id if r.from_user_id == subject_id else r.from_user_id) for r in rels
        } - {None}
        users = await self._repo.users_visible(list(other_user), viewer_id, self._cid)  # type: ignore[arg-type]
        members = await self._repo.members_visible(
            [r.to_household_member_id for r in rels if r.to_household_member_id],
            viewer_id,
            self._cid,
        )
        out: list[RelationOut] = []
        for r in rels:
            outgoing = r.from_user_id == subject_id
            kind = inverse(r.kind) if outgoing else r.kind
            person: RelationPerson
            pronouns: str | None = None
            if r.to_household_member_id is not None:
                m = members.get(r.to_household_member_id)
                if m is None:
                    continue
                person = RelationPerson(
                    id=m.id, type="household", name=m.name, memorial=m.passed_on is not None
                )
            else:
                u = users.get(r.to_user_id if outgoing else r.from_user_id)  # type: ignore[arg-type]
                if u is None:
                    continue
                pronouns = u.pronouns
                person = RelationPerson(
                    id=u.id,
                    type="user",
                    name=u.display_name,
                    username=u.username,
                    avatar_url=u.avatar_url,
                    memorial=u.memorialized_at is not None,
                )
            out.append(
                RelationOut(
                    id=r.id,
                    status=r.status,
                    kind=kind,
                    label=r.label,
                    display=r.label or derive([kind], pronouns),
                    direction=(
                        None
                        if r.status == "confirmed"
                        else ("outgoing" if outgoing else "incoming")
                    ),
                    person=person,
                )
            )
        return out

    async def list_for(self, user_id: uuid.UUID, viewer: User) -> list[RelationOut]:
        """
        @brief Relations of ``user_id`` as ``viewer`` may see them.
        @return Confirmed ones (plus your own pending ones on your own list).
        @throws NotFoundError when the user is missing or blocked either way.
        """
        await self._require_feature()
        target = await self._profiles.get_user(user_id, self._cid)
        is_self = viewer.id == user_id
        if target is None or (
            not is_self and await self._profiles.blocked_either_way(viewer.id, user_id)
        ):
            raise NotFoundError(message=_("User not found"))
        if not is_self:
            s = await self._profiles.get_settings(user_id)
            level = effective_levels(
                s.field_visibility if s else None, s.profile_visible_to if s else "community"
            )["relations"]
            shares = level == "groups" and await self._profiles.shares_group(viewer.id, user_id)
            if not allowed(level, is_self=False, shares_group=shares):
                return []
        rels = await self._repo.involving(self._cid, user_id)
        if not is_self:
            rels = [r for r in rels if r.status == "confirmed"]
        return await self._persons(rels, user_id, viewer.id)

    async def requests(self, actor: User) -> list[RelationOut]:
        """@brief Pending requests sent to the actor."""
        await self._require_feature()
        rels = await self._repo.pending_for(self._cid, actor.id)
        return await self._persons(rels, actor.id, actor.id)

    async def is_confirmed_relative(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        """@brief Direct family (parent, child, spouse, partner, sibling); not friend/other."""
        return await self._repo.confirmed_family_between(self._cid, a, b)

    async def graph(self, community_id: uuid.UUID) -> list[Relation]:
        """@brief Every confirmed relation (tree and nudges build on this)."""
        return await self._repo.graph(community_id)
