"""
@file tree_service.py
@brief Family tree and group relationship tree built from confirmed
       relations. Never leaks: people the viewer may not see are
       anonymous "private" nodes (edges kept), blocked people vanish, and
       the group tree returns members only (outsiders just yield a
       ``via_family`` edge).
"""

from __future__ import annotations

import heapq
import uuid
from collections import deque
from typing import NamedTuple

from app.core.exceptions import NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.household import HouseholdMember
from app.models.relation import Relation
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import FAMILY_KINDS, RelationRepository
from app.repositories.tree_repo import TreeRepository
from app.schemas.tree import TreeEdge, TreeNode, TreeOut
from app.services.profiles.visibility import allowed, effective_levels

MAX_NODES = 300
MAX_GENS = 10
VIA_MAX_HOPS = 4
_COST0 = ("spouse", "partner", "sibling")


class _Rel(NamedTuple):
    """@brief A relation as an oriented edge between node ids."""

    a: str
    b: str
    kind: str
    frm: uuid.UUID
    to_user: uuid.UUID | None


def _orient(r: Relation) -> _Rel:
    """@brief Node ids and edge kind; parent edges point parent -> child."""
    frm = f"u:{r.from_user_id}"
    to = f"u:{r.to_user_id}" if r.to_user_id else f"h:{r.to_household_member_id}"
    if r.kind == "child":
        return _Rel(to, frm, "parent", r.from_user_id, r.to_user_id)
    return _Rel(frm, to, r.kind, r.from_user_id, r.to_user_id)


class TreeService:
    """@brief Builds tree slices as one viewer may see them."""

    def __init__(
        self,
        relations: RelationRepository,
        tree: TreeRepository,
        profiles: ProfileRepository,
        communities: CommunityRepository,
        community_id: uuid.UUID,
        max_nodes: int = MAX_NODES,
    ) -> None:
        self._rel = relations
        self._tree = tree
        self._profiles = profiles
        self._communities = communities
        self._cid = community_id
        self._max = max_nodes

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._cid)
        if community is not None:
            require_feature(community, "family_tree")

    async def _hidden(self, ids: set[uuid.UUID], viewer: User) -> set[uuid.UUID]:
        """@brief Users whose "relations" field the viewer may not see."""
        settings = await self._tree.settings_for(list(ids))
        hidden: set[uuid.UUID] = set()
        for uid in ids:
            if uid == viewer.id:
                continue
            s = settings.get(uid)
            level = effective_levels(
                s.field_visibility if s else None, s.profile_visible_to if s else "community"
            )["relations"]
            shares = level == "groups" and await self._profiles.shares_group(viewer.id, uid)
            if not allowed(level, is_self=False, shares_group=shares):
                hidden.add(uid)
        return hidden

    def _user_node(self, u: User, s_birthday_shared: bool) -> TreeNode:
        """@brief Named user node; memorial dates only when the birthday is shared."""
        memorial = u.memorialized_at is not None
        shared = memorial and s_birthday_shared
        return TreeNode(
            id=f"u:{u.id}",
            name=u.display_name,
            avatar_url=u.avatar_url,
            kind="user",
            memorial=memorial,
            link=f"/app/u/{u.username}",
            born=u.birthday.isoformat() if shared and u.birthday else None,
            died=u.passed_on.isoformat() if shared and u.passed_on else None,
        )

    @staticmethod
    def _member_node(m: HouseholdMember) -> TreeNode:
        """@brief Named household node (already visible to the viewer)."""
        memorial = m.passed_on is not None
        return TreeNode(
            id=f"h:{m.id}",
            name=m.name,
            kind="household",
            memorial=memorial,
            link=f"/app/household/{m.id}",
            born=m.birthday.isoformat() if memorial and m.birthday and m.show_birth_year else None,
            died=m.passed_on.isoformat() if m.passed_on else None,
        )

    async def family(self, viewer: User, root: uuid.UUID | None = None, gens: int = 3) -> TreeOut:
        """
        @brief Nearby relatives of ``root`` (default: the viewer).
        @param viewer Requesting user.
        @param root User to center on.
        @param gens Generations to walk each way (1..10).
        @return Nodes (hidden ones masked), edges, ``truncated`` if cut off.
        @throws NotFoundError when root is missing, blocked or hides relations.
        """
        await self._require_feature()
        gens = max(1, min(gens, MAX_GENS))
        rels = [_orient(r) for r in await self._rel.graph(self._cid)]
        uids = {r.frm for r in rels} | {r.to_user for r in rels if r.to_user}
        uids.add(viewer.id)
        root_id = root or viewer.id
        users = await self._rel.users_visible(list(uids | {root_id}), viewer.id, self._cid)
        hidden = await self._hidden(set(users), viewer)
        if root_id not in users or root_id in hidden:
            raise NotFoundError(message=_("Person not found"))
        hids = [uuid.UUID(r.b[2:]) for r in rels if r.b.startswith("h:")]
        live = await self._tree.members_live(hids, self._cid)
        seen = await self._rel.members_visible(hids, viewer.id, self._cid)

        def valid(node: str) -> bool:
            if node.startswith("u:"):
                return uuid.UUID(node[2:]) in users
            m = live.get(uuid.UUID(node[2:]))
            return m is not None and m.kind == "person" and m.owner_id in users

        adj: dict[str, list[tuple[str, int]]] = {}
        usable = [r for r in rels if valid(r.a) and valid(r.b)]
        for r in usable:
            w = 0 if r.kind in _COST0 else 1
            adj.setdefault(r.a, []).append((r.b, w))
            adj.setdefault(r.b, []).append((r.a, w))

        def expandable(node: str) -> bool:
            return node.startswith("u:") and uuid.UUID(node[2:]) not in hidden

        start = f"u:{root_id}"
        cost = {start: 0}
        heap = [(0, 0, start)]
        tick = 0
        truncated = False
        done: set[str] = set()
        while heap:
            c, _t, node = heapq.heappop(heap)
            if node in done:
                continue
            done.add(node)
            if not expandable(node):
                continue
            for other, w in adj.get(node, []):
                nc = c + w
                if nc > gens:
                    truncated = truncated or other not in cost
                    continue
                if other in cost and cost[other] <= nc:
                    continue
                if other not in cost and len(cost) >= self._max:
                    truncated = True
                    continue
                cost[other] = nc
                tick += 1
                heapq.heappush(heap, (nc, tick, other))
        edges = {
            (r.a, r.b, r.kind)
            for r in usable
            if r.a in cost and r.b in cost and (expandable(r.a) or expandable(r.b))
        }
        return await self._render(cost, edges, users, seen, hidden, root_id, truncated)

    async def _render(
        self,
        order: dict[str, int],
        edges: set[tuple[str, str, str]],
        users: dict[uuid.UUID, User],
        seen: dict[uuid.UUID, HouseholdMember],
        hidden: set[uuid.UUID],
        root_id: uuid.UUID,
        truncated: bool,
    ) -> TreeOut:
        """@brief Turn node ids into named or private nodes."""
        uid_list = [uuid.UUID(n[2:]) for n in order if n.startswith("u:")]
        settings = await self._tree.settings_for(uid_list)
        live = await self._tree.members_live(
            [uuid.UUID(n[2:]) for n in order if n.startswith("h:")], self._cid
        )
        alias: dict[str, str] = {}
        priv = 0
        nodes: list[TreeNode] = []
        for nid in sorted(order, key=lambda n: (order[n], n)):
            node: TreeNode | None = None
            if nid.startswith("u:"):
                uid = uuid.UUID(nid[2:])
                s = settings.get(uid)
                shared = bool(s is None or s.show_birthday_to == "community")
                if uid not in hidden:
                    node = self._user_node(users[uid], shared)
            else:
                mid = uuid.UUID(nid[2:])
                if mid in seen and mid in live:
                    node = self._member_node(seen[mid])
            if node is None:
                priv += 1
                alias[nid] = f"p:{priv}"
                nodes.append(TreeNode(id=alias[nid], name=_("Private relative"), kind="private"))
            else:
                alias[nid] = nid
                nodes.append(node)
        pairs = sorted({(alias[a], alias[b], k) for a, b, k in edges})
        out_edges = [TreeEdge(a=a, b=b, kind=k) for a, b, k in pairs]
        return TreeOut(nodes=nodes, edges=out_edges, root=f"u:{root_id}", truncated=truncated)

    async def group(self, viewer: User, slug: str) -> TreeOut:
        """
        @brief Relations among the members of a group the viewer belongs to.
        @param slug Group slug.
        @return Members only; pairs linked through outsiders get a
                ``via_family`` edge that names nobody in between.
        @throws NotFoundError unknown group or viewer is not a member.
        """
        await self._require_feature()
        group = await self._tree.group_by_slug(slug, self._cid)
        member_ids = await self._tree.group_member_ids(group.id) if group else set()
        if group is None or viewer.id not in member_ids:
            raise NotFoundError(message=_("Group not found"))
        rels = [_orient(r) for r in await self._rel.graph(self._cid) if r.to_user_id is not None]
        uids = {r.frm for r in rels} | {r.to_user for r in rels if r.to_user} | member_ids
        users = await self._rel.users_visible(list(uids), viewer.id, self._cid)
        hidden = await self._hidden(set(users), viewer)
        members = member_ids & set(users)
        usable = [
            r
            for r in rels
            if r.frm in users
            and r.to_user in users
            and not (r.frm in hidden and r.to_user in hidden)
        ]
        direct: set[tuple[str, str, str]] = set()
        linked: set[frozenset[str]] = set()
        for r in usable:
            if r.frm in members and r.to_user in members:
                direct.add((r.a, r.b, r.kind))
                linked.add(frozenset((r.a, r.b)))
        for a, b in self._via_pairs(usable, members):
            if frozenset((a, b)) not in linked:
                direct.add((a, b, "via_family"))
        settings = await self._tree.settings_for(list(members))
        nodes = [
            self._user_node(users[m], m in settings and settings[m].show_birthday_to == "community")
            for m in sorted(members, key=str)
        ]
        edges = [TreeEdge(a=a, b=b, kind=k) for a, b, k in sorted(direct)]
        return TreeOut(nodes=nodes, edges=edges, root=f"u:{viewer.id}")

    @staticmethod
    def _via_pairs(usable: list[_Rel], members: set[uuid.UUID]) -> set[tuple[str, str]]:
        """@brief Member pairs joined by a family path (<= 4 hops) through non-members."""
        adj: dict[uuid.UUID, list[uuid.UUID]] = {}
        for r in usable:
            if r.kind in FAMILY_KINDS and r.to_user:
                adj.setdefault(r.frm, []).append(r.to_user)
                adj.setdefault(r.to_user, []).append(r.frm)
        pairs: set[tuple[str, str]] = set()
        for start in members:
            seen = {start}
            queue = deque([(start, 0)])
            while queue:
                node, d = queue.popleft()
                for nxt in adj.get(node, []):
                    if nxt in seen or d + 1 > VIA_MAX_HOPS:
                        continue
                    seen.add(nxt)
                    if nxt in members:
                        if d >= 1:
                            a, b = sorted((f"u:{start}", f"u:{nxt}"))
                            pairs.add((a, b))
                    else:
                        queue.append((nxt, d + 1))
        return pairs
