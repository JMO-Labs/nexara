# ruff: noqa: F811
"""
@file test_audit_admin_views.py
@brief Audit list filters, CSV export, no-DELETE guarantee and retention purge.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

import app.models  # noqa: F401
from app.api.v1.admin_audit import get_admin_audit_service
from app.core.deps_signins import get_admin_signin_service
from app.models.audit import AuditLog
from app.repositories.audit_repo import AuditRepository
from app.repositories.retention_repo import RetentionRepository
from app.repositories.signin_repo import SigninRepository
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_signin_service import AdminSigninService
from app.services.retention_service import purge_audit_log
from tests.integration.api.audit_world import CID, PW, FakeValkey, one, world  # noqa: F401


async def test_signins_export_and_audit_csv(world):
    w = world

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def reader():
        yield w.s

    w.app.dependency_overrides[get_admin_audit_service] = lambda: AdminAuditService(
        w.s, w.admin.id, "1.2.3.4", reader
    )
    w.app.dependency_overrides[get_admin_signin_service] = lambda: AdminSigninService(
        SigninRepository(w.s), CID, AuditRepository(w.s), w.admin.id, None, w.s.commit, reader
    )
    async with w.client() as c:
        r = await c.get("/api/v1/admin/signins.csv")
        assert r.status_code == 200
        got = await w.rows("signins.exported")
        assert len(got) == 1 and got[0].actor_id == w.admin.id
        await AuditRepository(w.s).append(
            actor_id=w.admin.id, action="x.evil", target_type="=cmd|calc", ip_address="9.9.9.9"
        )
        r = await c.get("/api/v1/admin/audit.csv?action_prefix=x.evil")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
        lines = r.text.splitlines()
        assert lines[0] == "time,actor,action,target_type,target_id,ip,details"
        assert len(lines) == 2 and "'=cmd|calc" in lines[1] and "x.evil" in lines[1]
        await one_export(w)
        assert (await c.delete("/api/v1/admin/audit")).status_code == 405
        assert (await c.delete("/api/v1/admin/audit-log")).status_code == 405
    paths = w.app.openapi()["paths"]
    audit = {p: m for p, m in paths.items() if p.startswith("/api/v1/admin/audit")}
    assert audit and all(not {"delete", "put", "patch"} & set(m) for m in audit.values())
    from app.api.v1.admin_audit import router as audit_router

    assert {m for r in audit_router.routes for m in getattr(r, "methods", ())} == {"GET"}


async def one_export(w):
    got = await w.rows("audit.exported")
    assert len(got) == 1 and got[0].actor_id == w.admin.id and got[0].target_type == "audit_log"


async def test_audit_list_filters(world):
    w = world
    repo = AuditRepository(w.s)
    now = datetime.now(UTC)
    for action, age in (
        ("zz.old", 10),
        ("zz.new", 1),
        ("yy.other", 1),
        ("qq_x.a", 1),
        ("qqyx.b", 1),
    ):
        e = await repo.append(actor_id=w.member.id, action=action, ip_address="10.1.2.3")
        await w.s.execute(
            text("update audit_log set created_at=:t where id=:i"),
            {"t": now - timedelta(days=age), "i": e.id},
        )
    async with w.client() as c:
        base = "/api/v1/admin/audit"

        async def get(qs):
            r = await c.get(f"{base}?{qs}")
            assert r.status_code == 200, r.text
            return [i["action"] for i in r.json()["items"]]

        assert sorted(await get("action_prefix=zz.")) == ["zz.new", "zz.old"]
        assert await get(f"actor_id={w.member.id}&q=yy") == ["yy.other"]
        assert await get(f"actor_id={w.member.id}&q=10.1.2") != []
        assert await get(f"actor_id={w.member.id}&q={w.member.display_name[:6]}") != []
        since = (now - timedelta(days=5)).isoformat().replace("+", "%2B")
        assert sorted(await get(f"actor_id={w.member.id}&since={since}&action_prefix=z")) == [
            "zz.new"
        ]
        until = (now - timedelta(days=5)).isoformat().replace("+", "%2B")
        assert await get(f"actor_id={w.member.id}&until={until}") == ["zz.old"]
        assert await get(f"actor_id={w.member.id}&q=%25") == []  # literal percent
        assert await get("action_prefix=qq_x.") == ["qq_x.a"]  # "_" is not a wildcard
        naive = (now - timedelta(days=5)).replace(tzinfo=None).isoformat()
        got = await get(f"actor_id={w.member.id}&since={naive}")  # naive = UTC
        assert sorted(got) == ["qq_x.a", "qqyx.b", "yy.other", "zz.new"]
        async with w.client(w.member) as m:
            assert (await m.get(f"{base}")).status_code == 403
            assert (await m.get(f"{base}.csv")).status_code == 403


async def _aged(w, *ages):
    repo, now, ids = AuditRepository(w.s), datetime.now(UTC), {}
    for age in ages:
        e = await repo.append(actor_id=w.admin.id, action=f"ret.d{age}")
        ids[age] = e.id
        await w.s.execute(
            text("update audit_log set created_at=:t where id=:i"),
            {"t": now - timedelta(days=age), "i": e.id},
        )
    return ids


async def _policy(w, enabled, days):
    await RetentionRepository(w.s).upsert("audit_logs", enabled, days, False, None)


async def test_retention_default_purges_past_365(world):
    w = world
    await w.s.execute(text("delete from retention_policies where policy_key='audit_logs'"))
    ids = await _aged(w, 366, 364)
    assert await purge_audit_log(w.s) >= 1
    assert await w.s.get(AuditLog, ids[366]) is None
    assert await w.s.get(AuditLog, ids[364]) is not None


async def test_retention_custom_730_keeps_400_day_row(world):
    w = world
    await _policy(w, True, 730)
    ids = await _aged(w, 731, 400)
    await purge_audit_log(w.s)
    assert await w.s.get(AuditLog, ids[731]) is None
    assert await w.s.get(AuditLog, ids[400]) is not None


async def test_retention_disabled_purges_nothing(world):
    w = world
    await _policy(w, False, 365)
    ids = await _aged(w, 2000)
    assert await purge_audit_log(w.s) == 0
    assert await w.s.get(AuditLog, ids[2000]) is not None


async def test_retention_clamps_below_365(world):
    w = world
    await _policy(w, True, 30)
    ids = await _aged(w, 100)
    await purge_audit_log(w.s)
    assert await w.s.get(AuditLog, ids[100]) is not None
