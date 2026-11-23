"""
@file test_memorial_service.py
@brief Unit tests for MemorialService and memorial exclusions in repos.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppError, AuthorizationError, ValidationError
from app.models.community import Community
from app.models.household import HouseholdMember
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.tag_repo import TagRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.services.memorial_service import MemorialService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER = uuid.uuid4()


def _svc(features: dict | None = None):
    comm = MagicMock(spec=Community)
    comm.features = features or {}
    communities = AsyncMock(spec=CommunityRepository)
    communities.get.return_value = comm
    parts = {
        "household": AsyncMock(spec=HouseholdRepository),
        "users": AsyncMock(spec=UserRepository),
        "tokens": AsyncMock(spec=TokenRepository),
        "audit": AsyncMock(spec=AuditRepository),
    }
    return MemorialService(communities=communities, community_id=CID, **parts), parts


def _user(uid=None, role="member"):
    u = MagicMock(spec=User)
    u.id, u.role, u.birthday = uid or uuid.uuid4(), role, date(1931, 5, 1)
    return u


def _member(birthday=date(1931, 5, 1)):
    m = MagicMock(spec=HouseholdMember)
    m.owner_id, m.birthday = OWNER, birthday
    return m


async def test_owner_sets_passed_on():
    svc, p = _svc()
    p["household"].get.return_value = _member()
    await svc.set_passed_on(uuid.uuid4(), _user(OWNER), date(2026, 1, 2))
    assert p["household"].update.await_args.args[1] == {"passed_on": date(2026, 1, 2)}


async def test_admin_may_set_and_clear():
    svc, p = _svc()
    p["household"].get.return_value = _member()
    await svc.set_passed_on(uuid.uuid4(), _user(role="admin"), None)
    p["household"].update.assert_awaited()


async def test_non_owner_forbidden():
    svc, p = _svc()
    p["household"].get.return_value = _member()
    with pytest.raises(AuthorizationError):
        await svc.set_passed_on(uuid.uuid4(), _user(), date(2026, 1, 2))


async def test_future_date_422():
    svc, p = _svc()
    p["household"].get.return_value = _member()
    with pytest.raises(ValidationError) as exc:
        await svc.set_passed_on(
            uuid.uuid4(), _user(OWNER), datetime.now(UTC).date() + timedelta(days=2)
        )
    assert exc.value.status_code == 422


async def test_before_birthday_422():
    svc, p = _svc()
    p["household"].get.return_value = _member()
    with pytest.raises(ValidationError):
        await svc.set_passed_on(uuid.uuid4(), _user(OWNER), date(1900, 1, 1))


async def test_feature_off_404():
    svc, p = _svc({"memorials": False})
    with pytest.raises(AppError) as exc:
        await svc.set_passed_on(uuid.uuid4(), _user(OWNER), None)
    assert exc.value.status_code == 404


async def test_memorialize_locks_revokes_and_audits():
    svc, p = _svc()
    target = _user()
    p["users"].get_by_id.return_value = target
    admin = _user(role="admin")
    await svc.memorialize_user(target.id, admin, date(2026, 3, 3))
    fields = p["users"].update.await_args.args[1]
    assert fields["is_active"] is False and fields["memorialized_at"] is not None
    p["tokens"].revoke_all_for_user.assert_awaited_with(target.id)
    assert p["audit"].append.await_args.kwargs["action"] == "admin.user.memorialized"


async def test_memorialize_admin_only():
    svc, _ = _svc()
    with pytest.raises(AuthorizationError):
        await svc.memorialize_user(uuid.uuid4(), _user(), None)


async def test_unmemorialize_restores():
    svc, p = _svc()
    p["users"].get_by_id.return_value = _user()
    await svc.unmemorialize_user(uuid.uuid4(), _user(role="admin"))
    fields = p["users"].update.await_args.args[1]
    assert fields == {"memorialized_at": None, "passed_on": None, "is_active": True}
    assert p["audit"].append.await_args.kwargs["action"] == "admin.user.unmemorialized"


async def test_mention_lookup_excludes_memorialized():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=[]))
    await TagRepository(session).users_by_username(CID, ["ruth"])
    sql = str(session.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "memorialized_at IS NULL" in sql


async def test_confirmed_relative_of_owner_sets_passed_on():
    from app.services.relation_service import RelationService

    svc, p = _svc()
    rel = AsyncMock(spec=RelationService)
    rel.is_confirmed_relative.return_value = True
    svc._relations = rel
    p["household"].get.return_value = _member()
    actor = _user()
    await svc.set_passed_on(uuid.uuid4(), actor, date(2026, 1, 2))
    rel.is_confirmed_relative.assert_awaited_once_with(actor.id, OWNER)
    rel.is_confirmed_relative.return_value = False
    with pytest.raises(AuthorizationError):
        await svc.set_passed_on(uuid.uuid4(), _user(), date(2026, 1, 2))
