"""
@file test_tree_service.py
@brief Unit tests for TreeService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.community import Community
from app.models.relation import Relation
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.repositories.tree_repo import TreeRepository
from app.services.tree_service import TreeService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _u(i: int) -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.display_name, u.username = uuid.UUID(int=i), f"U{i}", f"u{i}"
    u.avatar_url, u.memorialized_at, u.birthday, u.passed_on = None, None, None, None
    return u


def _r(frm: int, to: int, kind: str = "parent") -> MagicMock:
    r = MagicMock(spec=Relation)
    r.from_user_id, r.to_user_id, r.kind = uuid.UUID(int=frm), uuid.UUID(int=to), kind
    r.to_household_member_id = None
    return r


def _svc(rels, count=50, features=None, max_nodes=300):
    repo = AsyncMock(spec=RelationRepository)
    repo.graph.return_value = rels
    users = {uuid.UUID(int=i): _u(i) for i in range(1, count)}
    repo.users_visible.side_effect = lambda ids, v, c: {i: users[i] for i in ids if i in users}
    repo.members_visible.return_value = {}
    tree = AsyncMock(spec=TreeRepository)
    tree.settings_for.return_value = {}
    tree.members_live.return_value = {}
    comm = AsyncMock(spec=CommunityRepository)
    c = MagicMock(spec=Community)
    c.features = features or {}
    comm.get.return_value = c
    return (
        TreeService(repo, tree, AsyncMock(spec=ProfileRepository), comm, CID, max_nodes=max_nodes),
        users,
    )


async def test_parent_edges_point_parent_to_child() -> None:
    # 1 is parent of 2; 2 is child of 3 (so 3 is parent of 2)
    svc, users = _svc([_r(1, 2, "parent"), _r(2, 3, "child")])
    out = await svc.family(users[uuid.UUID(int=2)])
    pairs = {(e.a, e.b) for e in out.edges}
    assert pairs == {(f"u:{uuid.UUID(int=1)}", f"u:{uuid.UUID(int=2)}"),
                     (f"u:{uuid.UUID(int=3)}", f"u:{uuid.UUID(int=2)}")}  # fmt: skip
    assert not out.truncated


async def test_cap_sets_truncated() -> None:
    rels = [_r(1, i, "parent") for i in range(2, 12)]
    svc, users = _svc(rels, max_nodes=5)
    out = await svc.family(users[uuid.UUID(int=1)])
    assert len(out.nodes) == 5 and out.truncated


async def test_generation_limit_truncates() -> None:
    svc, users = _svc([_r(1, 2), _r(2, 3), _r(3, 4)])
    out = await svc.family(users[uuid.UUID(int=1)], gens=1)
    assert len(out.nodes) == 2 and out.truncated
    out = await svc.family(users[uuid.UUID(int=1)], gens=3)
    assert len(out.nodes) == 4 and not out.truncated


async def test_blocked_user_missing_from_visible_is_dropped() -> None:
    svc, users = _svc([_r(1, 2), _r(1, 99)])
    out = await svc.family(users[uuid.UUID(int=1)])
    assert len(out.nodes) == 2 and len(out.edges) == 1


async def test_feature_off_and_missing_root() -> None:
    svc, users = _svc([], features={"family_tree": False})
    with pytest.raises(AppError):
        await svc.family(users[uuid.UUID(int=1)])
    svc, users = _svc([])
    with pytest.raises(NotFoundError):
        await svc.family(users[uuid.UUID(int=1)], root=uuid.UUID(int=999))


def test_via_family_hop_limit() -> None:
    from app.services.tree_service import _orient

    def rel(a, b):
        return _orient(_r(a, b, "parent"))

    members = {uuid.UUID(int=1), uuid.UUID(int=6)}
    # 1-2-3-4-5-6 is 5 hops: too far; 1-2-3-4-6 is 4: ok
    far = [rel(1, 2), rel(2, 3), rel(3, 4), rel(4, 5), rel(5, 6)]
    near = [rel(1, 2), rel(2, 3), rel(3, 4), rel(4, 6)]
    assert TreeService._via_pairs(far, members) == set()
    assert len(TreeService._via_pairs(near, members)) == 1
