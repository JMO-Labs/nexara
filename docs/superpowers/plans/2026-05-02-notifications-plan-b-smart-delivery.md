# Notifications Refactor — Plan B: Smart Delivery

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add coalescing (group windows), Do-Not-Disturb (schedule + manual snooze), digest cadence, and the webhook channel (per-user + per-community) on top of the Plan A foundation.

**Architecture:** Each feature is a discrete service module composed into the existing dispatcher. The coalescer rewrites `NotificationService.notify` to call `repo.upsert_grouped`. DnD/digest sit between effective-prefs resolution and channel dispatch. Webhooks are a new `Channel` implementation backed by a Celery task with HMAC signing and exponential retry.

**Tech Stack:** Same as Plan A + `httpx` (already installed) for webhook delivery, `pytz` / `zoneinfo` (stdlib) for DnD time math.

**Spec:** `docs/superpowers/specs/2026-05-02-notifications-refactor-design.md` (sections 6.1, 6.3, 6.4, 6.5, 7, 8.2).

**Prerequisites:** Plan A complete and merged. Migration `b2c3d4e5f6a7` applied.

**Migration revision id used in this plan:** `c3d4e5f6a7b8`. **Down-revision:** `b2c3d4e5f6a7`.

---

## File Structure

| Path | Status | Purpose |
|---|---|---|
| `backend/alembic/versions/c3d4e5f6a7b8_notifications_v2_smart_delivery.py` | Create | DnD cols, digest queue + cadence, webhook subs table |
| `backend/app/models/user_settings.py` | Modify | Add `dnd_schedule`, `dnd_until`, `dnd_timezone`, `digest_cadence`, `digest_last_sent_at` |
| `backend/app/models/notification.py` | (no change — Plan A added grouped cols) | — |
| `backend/app/models/webhook.py` | Create | `WebhookSubscription` (per-user + per-community) |
| `backend/app/models/digest.py` | Create | `NotificationDigestQueueRow` |
| `backend/app/repositories/notification_repo.py` | Modify | `upsert_grouped` |
| `backend/app/repositories/webhook_repo.py` | Create | CRUD + filter by type_keys |
| `backend/app/repositories/digest_repo.py` | Create | enqueue + drain |
| `backend/app/services/notifications/coalescer.py` | Create | Group-key window UPSERT helper |
| `backend/app/services/notifications/dnd.py` | Create | Schedule + snooze evaluation |
| `backend/app/services/notifications/digest.py` | Create | Cadence eval + drain + render |
| `backend/app/services/notifications/channels/webhook.py` | Create | Webhook channel (HMAC + Celery) |
| `backend/app/services/notification_service.py` | Modify | Use coalescer; gate DnD; queue digest emails; expose snooze + DnD CRUD |
| `backend/app/services/notifications/dispatcher.py` | Modify | Suppress push on coalesced row inside window; register webhook channel |
| `backend/app/tasks/notification_tasks.py` | Modify | `digest_dispatch` beat task; `webhook_deliver` task; `send_digest_email` task |
| `backend/app/tasks/celery_app.py` | Modify | Beat schedule entry for `digest_dispatch` (every 5 min) |
| `backend/app/api/v1/notifications.py` | Modify | `/snooze`, `/preferences` (DnD + digest fields), `/webhooks` CRUD |
| `backend/app/api/v1/communities.py` | Modify | `/communities/{id}/webhooks` admin CRUD |
| `backend/app/schemas/notification.py` | Modify | DnD + digest schemas |
| `backend/app/schemas/webhook.py` | Create | Webhook request/response schemas |
| `backend/app/services/realtime/events.py` | Modify | Add `user_preferences_updated` event |
| `backend/tests/unit/services/notifications/test_coalescer.py` | Create | UPSERT happy path + race + window expiry |
| `backend/tests/unit/services/notifications/test_dnd.py` | Create | tz/DST + snooze + bypass |
| `backend/tests/unit/services/notifications/test_digest.py` | Create | cadence + drain + last_sent_at |
| `backend/tests/unit/services/notifications/channels/test_webhook.py` | Create | HMAC sig + retry + auto-disable |
| `backend/tests/unit/repositories/test_webhook_repo.py` | Create | CRUD + type_keys filter |
| `backend/tests/unit/repositories/test_digest_repo.py` | Create | enqueue + drain |
| `backend/tests/integration/api/test_webhooks_api.py` | Create | User + admin endpoints |
| `backend/tests/integration/api/test_snooze_api.py` | Create | Snooze + DnD prefs round-trip |
| `backend/tests/integration/migrations/test_notif_v2_smart_delivery.py` | Create | Verify new tables/cols |

---

## Task 1: Migration v2.5 — DnD, digest, webhooks

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_notifications_v2_smart_delivery.py`
- Modify: `backend/app/models/user_settings.py`
- Create: `backend/app/models/webhook.py`
- Create: `backend/app/models/digest.py`
- Test: `backend/tests/integration/migrations/test_notif_v2_smart_delivery.py`

- [ ] **Step 1: Confirm head**

```bash
cd backend && alembic heads
```
Expected: `b2c3d4e5f6a7 (head)`. If not, update `down_revision`.

- [ ] **Step 2: Write failing migration test**

`backend/tests/integration/migrations/test_notif_v2_smart_delivery.py`:

```python
"""@file test_notif_v2_smart_delivery.py @brief Verify v2.5 schema changes."""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings


@pytest.fixture()
def alembic_cfg():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL_SYNC)
    return cfg


def test_v2_smart_delivery_schema(alembic_cfg):
    eng = create_engine(get_settings().DATABASE_URL_SYNC, future=True)
    command.upgrade(alembic_cfg, "c3d4e5f6a7b8")
    with eng.begin() as conn:
        cols = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'user_settings'
        """)).scalars().all()
        for c in ("dnd_schedule", "dnd_until", "dnd_timezone",
                  "digest_cadence", "digest_last_sent_at"):
            assert c in cols

        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)).scalars().all()
        assert "webhook_subscriptions" in tables
        assert "notification_digest_queue" in tables

        # webhook_subscriptions partial indexes
        idx = conn.execute(text("""
            SELECT indexname FROM pg_indexes WHERE tablename = 'webhook_subscriptions'
        """)).scalars().all()
        assert any("community" in i for i in idx)
        assert any("user" in i for i in idx)
```

- [ ] **Step 3: Run, verify FAIL**

```bash
cd backend && pytest tests/integration/migrations/test_notif_v2_smart_delivery.py -xvs
```
Expected: revision not found.

- [ ] **Step 4: Author migration**

`backend/alembic/versions/c3d4e5f6a7b8_notifications_v2_smart_delivery.py`:

```python
"""notifications v2 smart delivery: DnD + digest + webhooks.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-02
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column(
        "dnd_schedule", postgresql.JSONB(), nullable=True,
    ))
    op.add_column("user_settings", sa.Column(
        "dnd_until", sa.DateTime(timezone=True), nullable=True,
    ))
    op.add_column("user_settings", sa.Column(
        "dnd_timezone", sa.Text(), nullable=False, server_default="UTC",
    ))
    op.add_column("user_settings", sa.Column(
        "digest_cadence", postgresql.JSONB(),
        nullable=False, server_default=sa.text("'{}'::jsonb"),
    ))
    op.add_column("user_settings", sa.Column(
        "digest_last_sent_at", sa.DateTime(timezone=True), nullable=True,
    ))

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.func.gen_random_uuid()),
        sa.Column("community_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("communities.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("type_keys", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("webhook_subs_community_idx", "webhook_subscriptions",
                    ["community_id"], postgresql_where=sa.text("enabled"))
    op.create_index("webhook_subs_user_idx", "webhook_subscriptions",
                    ["user_id"], postgresql_where=sa.text("enabled AND user_id IS NOT NULL"))

    op.create_table(
        "notification_digest_queue",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("type_key", sa.Text(), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("notifications.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id", "notification_id"),
    )
    op.create_index("digest_queue_drain_idx", "notification_digest_queue",
                    ["user_id", "type_key", "enqueued_at"])


def downgrade() -> None:
    op.drop_index("digest_queue_drain_idx", table_name="notification_digest_queue")
    op.drop_table("notification_digest_queue")
    op.drop_index("webhook_subs_user_idx", table_name="webhook_subscriptions")
    op.drop_index("webhook_subs_community_idx", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")
    op.drop_column("user_settings", "digest_last_sent_at")
    op.drop_column("user_settings", "digest_cadence")
    op.drop_column("user_settings", "dnd_timezone")
    op.drop_column("user_settings", "dnd_until")
    op.drop_column("user_settings", "dnd_schedule")
```

- [ ] **Step 5: Add SQLAlchemy models**

Modify `backend/app/models/user_settings.py` — add:

```python
dnd_schedule: Mapped[dict | None] = mapped_column(JSONB)
dnd_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
dnd_timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
digest_cadence: Mapped[dict] = mapped_column(
    JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"),
)
digest_last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`backend/app/models/webhook.py`:

```python
"""@file webhook.py @brief Outbound webhook subscriptions."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(Text, nullable=False)
    type_keys: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

`backend/app/models/digest.py`:

```python
"""@file digest.py @brief Per-user/per-type digest queue row."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationDigestQueueRow(Base):
    __tablename__ = "notification_digest_queue"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True,
    )
    type_key: Mapped[str] = mapped_column(Text, nullable=False)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

Register both in `backend/app/models/__init__.py`.

- [ ] **Step 6: Run, verify PASS**

```bash
cd backend && pytest tests/integration/migrations/test_notif_v2_smart_delivery.py -xvs
```

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/c3d4e5f6a7b8_notifications_v2_smart_delivery.py backend/app/models/ backend/tests/integration/migrations/test_notif_v2_smart_delivery.py
git commit -m "feat(notifications): DnD/digest/webhook schema (alembic v2.5)"
```

---

## Task 2: Coalescer

**Files:**
- Modify: `backend/app/repositories/notification_repo.py` (add `upsert_grouped`)
- Create: `backend/app/services/notifications/coalescer.py`
- Test: `backend/tests/unit/services/notifications/test_coalescer.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/test_coalescer.py`:

```python
"""@file test_coalescer.py @brief Group-key UPSERT semantics."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.repositories.notification_repo import NotificationRepository


@pytest.mark.asyncio
async def test_first_event_creates_row(db_session, seed_user, community_id) -> None:
    repo = NotificationRepository(db_session)
    n = await repo.upsert_grouped(
        seed_user.id, "reaction",
        {"message": "x", "actor_name": "A", "target_id": "p1"},
        group_key="reaction:p1", actor_id=uuid.uuid4(),
        community_id=community_id, group_window_seconds=600,
    )
    assert n.count == 1
    assert len(n.actor_ids) == 1


@pytest.mark.asyncio
async def test_second_event_within_window_increments_count(
    db_session, seed_user, community_id,
) -> None:
    repo = NotificationRepository(db_session)
    a1, a2 = uuid.uuid4(), uuid.uuid4()
    await repo.upsert_grouped(
        seed_user.id, "reaction",
        {"message": "x", "actor_name": "A", "target_id": "p1"},
        group_key="reaction:p1", actor_id=a1,
        community_id=community_id, group_window_seconds=600,
    )
    n2 = await repo.upsert_grouped(
        seed_user.id, "reaction",
        {"message": "y", "actor_name": "B", "target_id": "p1"},
        group_key="reaction:p1", actor_id=a2,
        community_id=community_id, group_window_seconds=600,
    )
    assert n2.count == 2
    assert set(n2.actor_ids) == {a1, a2}


@pytest.mark.asyncio
async def test_event_after_window_creates_new_row(
    db_session, seed_user, community_id,
) -> None:
    repo = NotificationRepository(db_session)
    n1 = await repo.upsert_grouped(
        seed_user.id, "reaction",
        {"message": "x", "target_id": "p1"},
        group_key="reaction:p1", actor_id=uuid.uuid4(),
        community_id=community_id, group_window_seconds=600,
    )
    # Force created_at into the past
    n1.created_at = datetime.now(UTC) - timedelta(hours=2)
    await db_session.flush()
    n2 = await repo.upsert_grouped(
        seed_user.id, "reaction",
        {"message": "y", "target_id": "p1"},
        group_key="reaction:p1", actor_id=uuid.uuid4(),
        community_id=community_id, group_window_seconds=600,
    )
    assert n2.id != n1.id
    assert n2.count == 1


@pytest.mark.asyncio
async def test_no_group_key_always_creates_row(
    db_session, seed_user, community_id,
) -> None:
    repo = NotificationRepository(db_session)
    a = await repo.upsert_grouped(
        seed_user.id, "mention", {"message": "x"}, group_key=None,
        actor_id=None, community_id=community_id, group_window_seconds=None,
    )
    b = await repo.upsert_grouped(
        seed_user.id, "mention", {"message": "y"}, group_key=None,
        actor_id=None, community_id=community_id, group_window_seconds=None,
    )
    assert a.id != b.id
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/test_coalescer.py -v
```

- [ ] **Step 3: Implement repo method**

Append to `backend/app/repositories/notification_repo.py`:

```python
async def upsert_grouped(
    self,
    user_id: uuid.UUID,
    type: str,
    payload: dict[str, Any],
    *,
    group_key: str | None,
    actor_id: uuid.UUID | None,
    community_id: uuid.UUID,
    group_window_seconds: int | None,
) -> Notification:
    """@brief Insert or merge an active grouped row; falls back to plain INSERT."""
    if group_key is None or group_window_seconds is None:
        return await self.create(user_id, type, payload, community_id)

    # Find an active grouped row inside the window
    cutoff = datetime.now(UTC) - timedelta(seconds=group_window_seconds)
    stmt = (
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.group_key == group_key,
            Notification.read_at.is_(None),
            Notification.dismissed_at.is_(None),
            Notification.created_at >= cutoff,
        )
        .order_by(Notification.created_at.desc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    res = await self._session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing is None:
        n = Notification(
            user_id=user_id, community_id=community_id, type=type,
            payload=payload, group_key=group_key,
            actor_ids=[actor_id] if actor_id else [],
        )
        self._session.add(n)
        await self._session.flush()
        await self._session.refresh(n)
        return n

    existing.count += 1
    existing.payload = payload
    if actor_id and actor_id not in existing.actor_ids:
        existing.actor_ids = [*existing.actor_ids, actor_id]
    existing.updated_at = datetime.now(UTC)
    await self._session.flush()
    await self._session.refresh(existing)
    return existing
```

- [ ] **Step 4: Implement coalescer module (thin wrapper for service composition)**

`backend/app/services/notifications/coalescer.py`:

```python
"""
@file coalescer.py
@brief Compose a group_key from a notification type + payload.target_id.
"""
from __future__ import annotations

from typing import Any

from app.services.notifications.registry import NotificationType


def compose_group_key(type: NotificationType, payload: dict[str, Any]) -> str | None:
    """@brief Returns ``"<type_key>:<target_id>"`` or ``None`` when not groupable."""
    if type.group_window_seconds is None:
        return None
    target = payload.get("target_id")
    if not target:
        return None
    return f"{type.key}:{target}"
```

- [ ] **Step 5: Wire coalescer into `NotificationService.notify`**

In `backend/app/services/notification_service.py`, replace the `await self._repo.create(...)` call inside `notify()` with:

```python
from app.services.notifications.coalescer import compose_group_key
...
group_key = compose_group_key(type_, validated.model_dump())
actor_id_str = validated.actor_id
actor_id = uuid.UUID(actor_id_str) if actor_id_str else None
notification = await self._repo.upsert_grouped(
    user_id, type_key, validated.model_dump(mode="json"),
    group_key=group_key, actor_id=actor_id,
    community_id=self._community_id,
    group_window_seconds=type_.group_window_seconds,
)
```

- [ ] **Step 6: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/test_coalescer.py tests/unit/services/test_notification_service.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/notification_repo.py backend/app/services/notifications/coalescer.py backend/app/services/notification_service.py backend/tests/unit/services/notifications/test_coalescer.py
git commit -m "feat(notifications): group-key windowed UPSERT coalescer"
```

---

## Task 3: DnD evaluator + snooze

**Files:**
- Create: `backend/app/services/notifications/dnd.py`
- Test: `backend/tests/unit/services/notifications/test_dnd.py`
- Modify: `backend/app/services/notification_service.py` (gate channels with DnD)
- Modify: `backend/app/api/v1/notifications.py` (snooze endpoints)

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/test_dnd.py`:

```python
"""@file test_dnd.py @brief Schedule + snooze evaluation (tz-aware)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.notifications.dnd import gate_channels, in_dnd
from app.services.notifications.registry import NotificationPayload, NotificationType


def _t(bypass: bool = False) -> NotificationType:
    return NotificationType(
        key="x", category="system", payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": True, "push": True, "toast": True},
        bypass_dnd=bypass, label_i18n="notif.x.label",
    )


def test_no_schedule_no_until_returns_false() -> None:
    assert in_dnd(schedule=None, until=None, tz="UTC", now=datetime.now(UTC)) is False


def test_dnd_until_in_future_returns_true() -> None:
    until = datetime.now(UTC) + timedelta(hours=1)
    assert in_dnd(schedule=None, until=until, tz="UTC", now=datetime.now(UTC)) is True


def test_dnd_until_expired_returns_false() -> None:
    until = datetime.now(UTC) - timedelta(minutes=1)
    assert in_dnd(schedule=None, until=until, tz="UTC", now=datetime.now(UTC)) is False


def test_schedule_overnight_window_handled() -> None:
    # 22:00 → 07:00 in user's tz; check 23:30 lands in window
    sched = {"mon": [{"start": "22:00", "end": "07:00"}]}
    tz = "America/New_York"
    # Construct a Monday 23:30 NY time; convert to UTC
    local = datetime(2026, 5, 4, 23, 30, tzinfo=ZoneInfo(tz))
    assert in_dnd(schedule=sched, until=None, tz=tz, now=local.astimezone(UTC)) is True


def test_schedule_outside_window_returns_false() -> None:
    sched = {"mon": [{"start": "22:00", "end": "07:00"}]}
    tz = "America/New_York"
    local = datetime(2026, 5, 4, 12, 0, tzinfo=ZoneInfo(tz))
    assert in_dnd(schedule=sched, until=None, tz=tz, now=local.astimezone(UTC)) is False


def test_gate_channels_suppresses_email_push_toast_in_dnd() -> None:
    eff = {"inapp": True, "email": True, "push": True, "toast": True}
    out = gate_channels(eff, type=_t(bypass=False), in_dnd_now=True)
    assert out == {"inapp": True, "email": False, "push": False, "toast": False}


def test_gate_channels_passthrough_when_bypass_dnd() -> None:
    eff = {"inapp": True, "email": True, "push": True, "toast": True}
    out = gate_channels(eff, type=_t(bypass=True), in_dnd_now=True)
    assert out == eff
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/test_dnd.py -v
```

- [ ] **Step 3: Implement**

`backend/app/services/notifications/dnd.py`:

```python
"""
@file dnd.py
@brief Do-Not-Disturb evaluation: weekly schedule + manual snooze + bypass.
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from app.services.notifications.registry import Channel, NotificationType

_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _in_window(now_local: datetime, start: time, end: time) -> bool:
    nt = now_local.time()
    if start <= end:
        return start <= nt < end
    # overnight: e.g. 22:00 → 07:00
    return nt >= start or nt < end


def in_dnd(
    *,
    schedule: dict[str, list[dict[str, str]]] | None,
    until: datetime | None,
    tz: str,
    now: datetime,
) -> bool:
    """@brief True if ``now`` (UTC) falls inside DnD per snooze or schedule."""
    if until is not None and until > now:
        return True
    if not schedule:
        return False
    try:
        zone = ZoneInfo(tz)
    except Exception:
        zone = ZoneInfo("UTC")
    local = now.astimezone(zone)
    day_key = _DAY_KEYS[local.weekday()]
    windows = schedule.get(day_key) or []
    for w in windows:
        try:
            start = _parse_hhmm(w["start"])
            end = _parse_hhmm(w["end"])
        except (KeyError, ValueError):
            continue
        if _in_window(local, start, end):
            return True
    return False


def gate_channels(
    effective: dict[Channel, bool],
    *,
    type: NotificationType,
    in_dnd_now: bool,
) -> dict[Channel, bool]:
    """@brief Suppress email/push/toast when in DnD unless type bypasses."""
    if not in_dnd_now or type.bypass_dnd:
        return effective
    out = dict(effective)
    for ch in ("email", "push", "toast"):
        out[ch] = False  # type: ignore[index]
    return out
```

- [ ] **Step 4: Wire into service**

In `backend/app/services/notification_service.py`, after computing `eff = effective_channels(...)`:

```python
from app.services.notifications.dnd import gate_channels, in_dnd
...
in_dnd_now = in_dnd(
    schedule=getattr(settings, "dnd_schedule", None),
    until=getattr(settings, "dnd_until", None),
    tz=getattr(settings, "dnd_timezone", "UTC"),
    now=datetime.now(UTC),
)
eff = gate_channels(eff, type=type_, in_dnd_now=in_dnd_now)
```

Add façade methods:

```python
async def set_dnd(
    self, user_id: uuid.UUID, *,
    schedule: dict | None = None, tz: str | None = None,
) -> None:
    s = await self._settings_repo.get_or_create(user_id, self._community_id)
    if schedule is not None:
        s.dnd_schedule = schedule
    if tz is not None:
        s.dnd_timezone = tz
    await self._settings_repo._session.flush()  # type: ignore[attr-defined]


async def snooze(self, user_id: uuid.UUID, until: datetime) -> None:
    s = await self._settings_repo.get_or_create(user_id, self._community_id)
    s.dnd_until = until
    await self._settings_repo._session.flush()  # type: ignore[attr-defined]


async def clear_snooze(self, user_id: uuid.UUID) -> None:
    s = await self._settings_repo.get_or_create(user_id, self._community_id)
    s.dnd_until = None
    await self._settings_repo._session.flush()  # type: ignore[attr-defined]
```

- [ ] **Step 5: Add API endpoints**

In `backend/app/api/v1/notifications.py`:

```python
class SnoozeRequest(BaseModel):
    duration: str  # "1h" | "until_morning" | iso8601


def _resolve_snooze_until(spec: str) -> datetime:
    now = datetime.now(UTC)
    if spec == "1h":
        return now + timedelta(hours=1)
    if spec == "until_morning":
        # Next 07:00 in UTC (UI calls with user-local conversion if needed)
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target
    return datetime.fromisoformat(spec)


@router.post("/snooze", response_model=MessageResponse)
async def snooze(
    body: SnoozeRequest,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    until = _resolve_snooze_until(body.duration)
    await service.snooze(user.id, until)
    return MessageResponse(message=_("Snoozed until {u}").format(u=until.isoformat()))


@router.delete("/snooze", response_model=MessageResponse)
async def clear_snooze(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    await service.clear_snooze(user.id)
    return MessageResponse(message=_("Snooze cleared"))
```

Extend `PreferencesResponse` + `PreferencesUpdate`:

```python
class PreferencesResponse(BaseModel):
    notification_prefs: dict[str, dict[str, bool]]
    dnd_schedule: dict | None
    dnd_until: datetime | None
    dnd_timezone: str
    digest_cadence: dict[str, str]


class PreferencesUpdate(BaseModel):
    notification_prefs: dict[str, dict[str, bool]] | None = None
    dnd_schedule: dict | None = None
    dnd_timezone: str | None = None
    digest_cadence: dict[str, str] | None = None
```

Update `GET /preferences` and `PATCH /preferences` handlers to read/write all four fields. Validate `digest_cadence` values in `("instant","hourly","daily","off")` else 400 `NOTIF_PREF_INVALID`.

- [ ] **Step 6: Add API tests**

`backend/tests/integration/api/test_snooze_api.py`:

```python
"""@file test_snooze_api.py @brief Snooze + DnD prefs round-trip."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_snooze_1h_persists(client_authed) -> None:
    res = await client_authed.post("/api/v1/notifications/snooze", json={"duration": "1h"})
    assert res.status_code == 200
    prefs = (await client_authed.get("/api/v1/notifications/preferences")).json()
    assert prefs["dnd_until"] is not None


@pytest.mark.asyncio
async def test_clear_snooze(client_authed) -> None:
    await client_authed.post("/api/v1/notifications/snooze", json={"duration": "1h"})
    await client_authed.delete("/api/v1/notifications/snooze")
    prefs = (await client_authed.get("/api/v1/notifications/preferences")).json()
    assert prefs["dnd_until"] is None


@pytest.mark.asyncio
async def test_set_dnd_schedule(client_authed) -> None:
    sched = {"mon": [{"start": "22:00", "end": "07:00"}]}
    res = await client_authed.patch(
        "/api/v1/notifications/preferences",
        json={"dnd_schedule": sched, "dnd_timezone": "America/New_York"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["dnd_schedule"] == sched
    assert body["dnd_timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_invalid_digest_cadence_rejected(client_authed) -> None:
    res = await client_authed.patch(
        "/api/v1/notifications/preferences",
        json={"digest_cadence": {"mention": "yearly"}},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "NOTIF_PREF_INVALID"
```

- [ ] **Step 7: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/test_dnd.py tests/integration/api/test_snooze_api.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/notifications/dnd.py backend/app/services/notification_service.py backend/app/api/v1/notifications.py backend/app/schemas/notification.py backend/tests/unit/services/notifications/test_dnd.py backend/tests/integration/api/test_snooze_api.py
git commit -m "feat(notifications): DnD schedule + manual snooze + bypass"
```

---

## Task 4: Digest queue + drain + Celery beat

**Files:**
- Create: `backend/app/repositories/digest_repo.py`
- Create: `backend/app/services/notifications/digest.py`
- Modify: `backend/app/services/notification_service.py` (queue email when cadence != instant)
- Modify: `backend/app/tasks/notification_tasks.py` (`digest_dispatch` + `send_digest_email`)
- Modify: `backend/app/tasks/celery_app.py` (beat schedule)
- Test: `backend/tests/unit/services/notifications/test_digest.py`
- Test: `backend/tests/unit/repositories/test_digest_repo.py`

- [ ] **Step 1: Failing repo test**

`backend/tests/unit/repositories/test_digest_repo.py`:

```python
"""@file test_digest_repo.py @brief Enqueue + drain ops."""
from __future__ import annotations

import uuid

import pytest

from app.repositories.digest_repo import DigestRepository
from app.repositories.notification_repo import NotificationRepository


@pytest.mark.asyncio
async def test_enqueue_then_drain_returns_in_order(
    db_session, seed_user, community_id,
) -> None:
    nrepo = NotificationRepository(db_session)
    drepo = DigestRepository(db_session)
    n1 = await nrepo.create(seed_user.id, "reaction", {"message": "1"}, community_id)
    n2 = await nrepo.create(seed_user.id, "reaction", {"message": "2"}, community_id)
    await drepo.enqueue(seed_user.id, "reaction", n1.id)
    await drepo.enqueue(seed_user.id, "reaction", n2.id)

    drained = await drepo.drain(seed_user.id, "reaction")
    assert [r.notification_id for r in drained] == [n1.id, n2.id]
    # Idempotent: second drain empty
    assert await drepo.drain(seed_user.id, "reaction") == []
```

- [ ] **Step 2: Implement repo**

`backend/app/repositories/digest_repo.py`:

```python
"""@file digest_repo.py @brief notification_digest_queue ops."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digest import NotificationDigestQueueRow


class DigestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self, user_id: uuid.UUID, type_key: str, notification_id: uuid.UUID,
    ) -> None:
        row = NotificationDigestQueueRow(
            user_id=user_id, type_key=type_key, notification_id=notification_id,
        )
        self._session.add(row)
        await self._session.flush()

    async def drain(
        self, user_id: uuid.UUID, type_key: str,
    ) -> list[NotificationDigestQueueRow]:
        stmt = (
            select(NotificationDigestQueueRow)
            .where(NotificationDigestQueueRow.user_id == user_id)
            .where(NotificationDigestQueueRow.type_key == type_key)
            .order_by(NotificationDigestQueueRow.enqueued_at.asc())
        )
        res = await self._session.execute(stmt)
        rows = list(res.scalars().all())
        if not rows:
            return []
        ids = [r.notification_id for r in rows]
        await self._session.execute(
            delete(NotificationDigestQueueRow).where(
                NotificationDigestQueueRow.user_id == user_id,
                NotificationDigestQueueRow.notification_id.in_(ids),
            )
        )
        await self._session.flush()
        return rows

    async def list_users_with_pending(self) -> list[uuid.UUID]:
        stmt = select(NotificationDigestQueueRow.user_id).distinct()
        res = await self._session.execute(stmt)
        return [r for r in res.scalars().all()]
```

- [ ] **Step 3: Failing service test**

`backend/tests/unit/services/notifications/test_digest.py`:

```python
"""@file test_digest.py @brief Cadence evaluation + last_sent_at."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.notifications.digest import should_send_now


def test_instant_never_drains() -> None:
    assert should_send_now("instant", last_sent_at=None, now=datetime.now(UTC), tz="UTC") is False


def test_off_never_drains() -> None:
    assert should_send_now("off", last_sent_at=None, now=datetime.now(UTC), tz="UTC") is False


def test_hourly_drains_when_never_sent() -> None:
    assert should_send_now("hourly", last_sent_at=None, now=datetime.now(UTC), tz="UTC") is True


def test_hourly_drains_after_an_hour() -> None:
    last = datetime.now(UTC) - timedelta(hours=1, minutes=1)
    assert should_send_now("hourly", last_sent_at=last, now=datetime.now(UTC), tz="UTC") is True


def test_hourly_skips_within_hour() -> None:
    last = datetime.now(UTC) - timedelta(minutes=30)
    assert should_send_now("hourly", last_sent_at=last, now=datetime.now(UTC), tz="UTC") is False


def test_daily_drains_after_local_hour_crossed() -> None:
    tz = "America/New_York"
    now_local = datetime(2026, 5, 4, 8, 5, tzinfo=ZoneInfo(tz))
    last = datetime(2026, 5, 3, 9, 0, tzinfo=ZoneInfo(tz)).astimezone(UTC)
    assert should_send_now("daily", last_sent_at=last,
                            now=now_local.astimezone(UTC), tz=tz) is True


def test_daily_skips_before_local_hour() -> None:
    tz = "America/New_York"
    now_local = datetime(2026, 5, 4, 6, 0, tzinfo=ZoneInfo(tz))
    last = datetime(2026, 5, 3, 9, 0, tzinfo=ZoneInfo(tz)).astimezone(UTC)
    assert should_send_now("daily", last_sent_at=last,
                            now=now_local.astimezone(UTC), tz=tz) is False
```

- [ ] **Step 4: Implement digest evaluator**

`backend/app/services/notifications/digest.py`:

```python
"""
@file digest.py
@brief Cadence evaluation for digest emails.

Defaults: daily digest sends at 08:00 in the user's timezone.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

DAILY_HOUR = 8


def should_send_now(
    cadence: str, *, last_sent_at: datetime | None, now: datetime, tz: str,
) -> bool:
    if cadence in ("instant", "off"):
        return False
    if cadence == "hourly":
        if last_sent_at is None:
            return True
        return (now - last_sent_at) >= timedelta(hours=1)
    if cadence == "daily":
        try:
            zone = ZoneInfo(tz)
        except Exception:
            zone = ZoneInfo("UTC")
        local = now.astimezone(zone)
        if local.hour < DAILY_HOUR:
            return False
        if last_sent_at is None:
            return True
        last_local = last_sent_at.astimezone(zone)
        return last_local.date() < local.date()
    return False
```

- [ ] **Step 5: Wire email channel to honor cadence**

In `backend/app/services/notification_service.py` `notify(...)`, after dispatch returns, when `eff.email is True`, override channel behavior — easier path: handle inline before calling dispatcher.

Replace `eff` post-DnD logic to split email into instant vs queued:

```python
cadence = (getattr(settings, "digest_cadence", None) or {}).get(type_key, "instant")
queue_email = eff.get("email") and cadence != "instant"
if queue_email:
    eff = {**eff, "email": False}    # dispatcher will skip email
notification = await self._repo.upsert_grouped(... )  # as in Task 2
await self._dispatcher.dispatch(notification, type_, eff)
if queue_email:
    from app.repositories.digest_repo import DigestRepository
    await DigestRepository(self._settings_repo._session).enqueue(  # type: ignore[attr-defined]
        user_id, type_key, notification.id,
    )
```

- [ ] **Step 6: Beat task**

In `backend/app/tasks/notification_tasks.py`:

```python
@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="app.tasks.notification_tasks.digest_dispatch", queue="notifications",
)
def digest_dispatch(self) -> dict[str, int]:
    """@brief Drain digest queue per user/type per cadence; spawn send_digest_email tasks."""
    return asyncio.run(_digest_dispatch_async())


async def _digest_dispatch_async() -> dict[str, int]:
    from app.repositories.digest_repo import DigestRepository
    from app.repositories.settings_repo import SettingsRepository
    from app.services.notifications.digest import should_send_now

    spawned = 0
    async with async_session_factory() as session:
        drepo = DigestRepository(session)
        srepo = SettingsRepository(session)
        for user_id in await drepo.list_users_with_pending():
            settings = await srepo.get_by_user_id(user_id)
            if settings is None:
                continue
            cadence_map = getattr(settings, "digest_cadence", {}) or {}
            tz = getattr(settings, "dnd_timezone", "UTC")
            last = getattr(settings, "digest_last_sent_at", None)
            now = datetime.now(UTC)
            for type_key, cadence in cadence_map.items():
                if not should_send_now(cadence, last_sent_at=last, now=now, tz=tz):
                    continue
                rows = await drepo.drain(user_id, type_key)
                if not rows:
                    continue
                send_digest_email.delay(
                    str(user_id), type_key, [str(r.notification_id) for r in rows],
                )
                spawned += 1
            settings.digest_last_sent_at = now
        await session.commit()
    return {"spawned": spawned}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="app.tasks.notification_tasks.send_digest_email",
    max_retries=3, queue="email",
)
def send_digest_email(self, user_id: str, type_key: str, ids: list[str]) -> dict[str, str]:
    """@brief Render & send a digest email summarising N notifications."""
    return asyncio.run(_send_digest_email_async(uuid.UUID(user_id), type_key, ids))


async def _send_digest_email_async(
    user_id: uuid.UUID, type_key: str, ids: list[str],
) -> dict[str, str]:
    from sqlalchemy import select
    from app.models.notification import Notification
    from app.services.email.sender import EmailSender
    from app.services.email.templates import EmailTemplateRenderer

    async with async_session_factory() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if user is None:
            return {"status": "skipped"}
        nres = await session.execute(
            select(Notification).where(Notification.id.in_([uuid.UUID(i) for i in ids]))
            .order_by(Notification.created_at.desc())
        )
        items = list(nres.scalars().all())

    renderer = EmailTemplateRenderer()
    html, text = renderer.render(
        "digest.html",
        {"type_key": type_key, "items": [
            {"message": i.payload.get("message", ""), "link": i.payload.get("link", ""),
             "created_at": i.created_at.isoformat()}
            for i in items
        ]},
    )
    sender = EmailSender()
    sent = await sender.send(
        to=user.email,
        subject=f"Your {type_key.replace('_', ' ')} digest",
        html_body=html, text_body=text,
    )
    return {"status": "sent" if sent else "skipped"}
```

Add a placeholder `backend/app/services/email/templates/digest.html` (basic Jinja2 list of `items`).

- [ ] **Step 7: Beat schedule**

In `backend/app/tasks/celery_app.py`, add to `beat_schedule`:

```python
"digest-dispatch-every-5min": {
    "task": "app.tasks.notification_tasks.digest_dispatch",
    "schedule": 300.0,  # seconds
},
```

- [ ] **Step 8: Verify PASS**

```bash
cd backend && pytest tests/unit/repositories/test_digest_repo.py tests/unit/services/notifications/test_digest.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/repositories/digest_repo.py backend/app/services/notifications/digest.py backend/app/services/notification_service.py backend/app/tasks/notification_tasks.py backend/app/tasks/celery_app.py backend/app/services/email/templates/digest.html backend/tests/unit/repositories/test_digest_repo.py backend/tests/unit/services/notifications/test_digest.py
git commit -m "feat(notifications): digest queue + cadence + every-5min beat"
```

---

## Task 5: Webhook channel + repo + CRUD

**Files:**
- Create: `backend/app/repositories/webhook_repo.py`
- Create: `backend/app/services/notifications/channels/webhook.py`
- Modify: `backend/app/tasks/notification_tasks.py` (`webhook_deliver`)
- Create: `backend/app/schemas/webhook.py`
- Modify: `backend/app/api/v1/notifications.py` (per-user webhook CRUD)
- Modify: `backend/app/api/v1/communities.py` (admin community-level CRUD)
- Modify: `backend/app/core/dependencies.py` (register `WebhookChannel` in dispatcher)
- Tests: `backend/tests/unit/repositories/test_webhook_repo.py`, `backend/tests/unit/services/notifications/channels/test_webhook.py`, `backend/tests/integration/api/test_webhooks_api.py`

- [ ] **Step 1: Failing repo test**

`backend/tests/unit/repositories/test_webhook_repo.py`:

```python
"""@file test_webhook_repo.py @brief Webhook subscription CRUD + filter."""
from __future__ import annotations

import uuid

import pytest

from app.repositories.webhook_repo import WebhookRepository


@pytest.mark.asyncio
async def test_create_and_list_for_user(db_session, seed_user, community_id) -> None:
    repo = WebhookRepository(db_session)
    sub = await repo.create(
        community_id=community_id, user_id=seed_user.id,
        url="https://example.test/hook", secret="s3cret", type_keys=["mention"],
    )
    rows = await repo.list_for_user(seed_user.id)
    assert any(r.id == sub.id for r in rows)


@pytest.mark.asyncio
async def test_list_matching_filters_by_type_keys_and_enabled(
    db_session, seed_user, community_id,
) -> None:
    repo = WebhookRepository(db_session)
    a = await repo.create(community_id=community_id, user_id=seed_user.id,
                          url="https://a.test", secret="x", type_keys=["mention"])
    b = await repo.create(community_id=community_id, user_id=None,
                          url="https://b.test", secret="x", type_keys=[])  # all types
    c = await repo.create(community_id=community_id, user_id=seed_user.id,
                          url="https://c.test", secret="x", type_keys=["reaction"])
    await repo.set_enabled(c.id, False)

    rows = await repo.list_matching(
        community_id=community_id, user_id=seed_user.id, type_key="mention",
    )
    ids = {r.id for r in rows}
    assert a.id in ids
    assert b.id in ids
    assert c.id not in ids


@pytest.mark.asyncio
async def test_record_failure_disables_after_threshold(
    db_session, seed_user, community_id,
) -> None:
    repo = WebhookRepository(db_session)
    sub = await repo.create(community_id=community_id, user_id=seed_user.id,
                            url="https://x.test", secret="x", type_keys=[])
    for _ in range(10):
        await repo.record_failure(sub.id)
    await db_session.refresh(sub)
    assert sub.enabled is False
```

- [ ] **Step 2: Implement repo**

`backend/app/repositories/webhook_repo.py`:

```python
"""@file webhook_repo.py @brief Webhook subscription repository."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookSubscription


class WebhookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, community_id: uuid.UUID, user_id: uuid.UUID | None,
        url: str, secret: str, type_keys: list[str],
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            community_id=community_id, user_id=user_id,
            url=url, secret=secret, type_keys=type_keys,
        )
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def get(self, sub_id: uuid.UUID) -> WebhookSubscription | None:
        return await self._session.get(WebhookSubscription, sub_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.user_id == user_id,
        ).order_by(WebhookSubscription.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_community(
        self, community_id: uuid.UUID,
    ) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.community_id == community_id,
            WebhookSubscription.user_id.is_(None),
        ).order_by(WebhookSubscription.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_matching(
        self, *, community_id: uuid.UUID, user_id: uuid.UUID, type_key: str,
    ) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.community_id == community_id,
            WebhookSubscription.enabled.is_(True),
            or_(
                WebhookSubscription.user_id == user_id,
                WebhookSubscription.user_id.is_(None),
            ),
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [
            r for r in rows
            if not r.type_keys or type_key in r.type_keys
        ]

    async def set_enabled(self, sub_id: uuid.UUID, enabled: bool) -> None:
        sub = await self.get(sub_id)
        if sub is not None:
            sub.enabled = enabled
            await self._session.flush()

    async def update(
        self, sub_id: uuid.UUID, *, url: str | None = None,
        type_keys: list[str] | None = None, enabled: bool | None = None,
    ) -> WebhookSubscription | None:
        sub = await self.get(sub_id)
        if sub is None:
            return None
        if url is not None:
            sub.url = url
        if type_keys is not None:
            sub.type_keys = type_keys
        if enabled is not None:
            sub.enabled = enabled
        await self._session.flush()
        return sub

    async def delete(self, sub_id: uuid.UUID) -> bool:
        sub = await self.get(sub_id)
        if sub is None:
            return False
        await self._session.delete(sub)
        await self._session.flush()
        return True

    async def record_failure(self, sub_id: uuid.UUID) -> None:
        sub = await self.get(sub_id)
        if sub is None:
            return
        sub.failure_count += 1
        sub.last_failure_at = datetime.now(UTC)
        if sub.failure_count >= 10:
            sub.enabled = False
        await self._session.flush()

    async def record_success(self, sub_id: uuid.UUID) -> None:
        sub = await self.get(sub_id)
        if sub is None:
            return
        sub.failure_count = 0
        sub.last_failure_at = None
        await self._session.flush()
```

- [ ] **Step 3: Failing channel test**

`backend/tests/unit/services/notifications/channels/test_webhook.py`:

```python
"""@file test_webhook.py @brief Webhook channel signs + queues per matching sub."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.notification import Notification
from app.services.notifications.channels.webhook import WebhookChannel, sign_payload


def test_sign_payload_format() -> None:
    sig = sign_payload("body", secret="s", ts=1714600000)
    parts = dict(p.split("=", 1) for p in sig.split(","))
    assert parts["t"] == "1714600000"
    assert parts["v1"] and len(parts["v1"]) == 64  # sha256 hex


@pytest.mark.asyncio
async def test_webhook_channel_enqueues_one_task_per_matching_sub() -> None:
    repo = MagicMock()
    repo.list_matching = AsyncMock(return_value=[
        MagicMock(id=uuid.uuid4(), url="https://a.test", secret="s", type_keys=[]),
        MagicMock(id=uuid.uuid4(), url="https://b.test", secret="s", type_keys=["mention"]),
    ])
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4(); n.community_id = uuid.uuid4()
    n.type = "mention"; n.payload = {"message": "x"}; n.actor_ids = []
    n.count = 1; n.created_at = MagicMock(); n.created_at.isoformat = lambda: "t"
    n.updated_at = MagicMock(); n.updated_at.isoformat = lambda: "t"

    with patch("app.services.notifications.channels.webhook.webhook_deliver") as task:
        ch = WebhookChannel(webhook_repo_factory=lambda: repo)
        result = await ch.send(n)

    assert task.delay.call_count == 2
    assert result.ok is True
```

- [ ] **Step 4: Implement channel + delivery task**

`backend/app/services/notifications/channels/webhook.py`:

```python
"""
@file webhook.py
@brief Webhook channel: looks up matching subscriptions and enqueues HMAC-signed POSTs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Callable

import structlog

from app.models.notification import Notification
from app.repositories.webhook_repo import WebhookRepository
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.registry import get as registry_get
from app.tasks.notification_tasks import webhook_deliver

logger = structlog.get_logger(__name__)


def sign_payload(body: str, *, secret: str, ts: int | None = None) -> str:
    if ts is None:
        ts = int(time.time())
    msg = f"{ts}.{body}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _build_payload(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "category": registry_get(n.type).category if n.type in __import__(
            "app.services.notifications.registry"
        ).services.notifications.registry._REGISTRY else "plugin",
        "user_id": str(n.user_id),
        "community_id": str(n.community_id),
        "payload": n.payload,
        "actor_ids": [str(a) for a in n.actor_ids],
        "count": n.count,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
    }


class WebhookChannel:
    key = "webhook"

    def __init__(
        self,
        webhook_repo_factory: Callable[[], WebhookRepository],
    ) -> None:
        self._repo_factory = webhook_repo_factory

    async def send(self, notification: Notification) -> ChannelResult:
        repo = self._repo_factory()
        try:
            subs = await repo.list_matching(
                community_id=notification.community_id,
                user_id=notification.user_id,
                type_key=notification.type,
            )
        except Exception as exc:
            logger.warning("notif.channel.failed", channel="webhook", error=str(exc))
            return ChannelResult(ok=False, error=str(exc))

        body = json.dumps(_build_payload(notification), separators=(",", ":"))
        for sub in subs:
            sig = sign_payload(body, secret=sub.secret)
            try:
                webhook_deliver.delay(str(sub.id), sub.url, body, sig)
            except Exception as exc:
                logger.warning("notif.channel.failed", channel="webhook",
                               sub_id=str(sub.id), error=str(exc))
                return ChannelResult(ok=False, error=str(exc))
        return ChannelResult(ok=True)
```

`backend/app/tasks/notification_tasks.py` add:

```python
@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="app.tasks.notification_tasks.webhook_deliver",
    queue="notifications", max_retries=5, retry_backoff=True,
    retry_backoff_max=600, retry_jitter=True,
    autoretry_for=(Exception,),
)
def webhook_deliver(self, sub_id: str, url: str, body: str, signature: str) -> dict[str, str]:
    """@brief POST signed payload; record success/failure on the sub."""
    import httpx
    headers = {"Content-Type": "application/json", "X-Nexara-Signature": signature}
    try:
        r = httpx.post(url, content=body, headers=headers, timeout=10.0)
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        asyncio.run(_record(sub_id, ok=False))
        raise self.retry(exc=exc)
    if 200 <= r.status_code < 300:
        asyncio.run(_record(sub_id, ok=True))
        return {"status": "delivered"}
    if 500 <= r.status_code < 600:
        asyncio.run(_record(sub_id, ok=False))
        raise self.retry(exc=Exception(f"upstream {r.status_code}"))
    # 4xx: count a failure but do not retry
    asyncio.run(_record(sub_id, ok=False))
    return {"status": f"http_{r.status_code}"}


async def _record(sub_id: str, *, ok: bool) -> None:
    from app.repositories.webhook_repo import WebhookRepository
    async with async_session_factory() as session:
        repo = WebhookRepository(session)
        if ok:
            await repo.record_success(uuid.UUID(sub_id))
        else:
            await repo.record_failure(uuid.UUID(sub_id))
        await session.commit()
```

- [ ] **Step 5: API CRUD**

`backend/app/schemas/webhook.py`:

```python
"""@file webhook.py @brief Webhook subscription schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class WebhookCreate(BaseModel):
    url: HttpUrl
    type_keys: list[str] = []


class WebhookCreateResponse(BaseModel):
    id: uuid.UUID
    url: str
    secret: str    # returned ONCE on create
    type_keys: list[str]
    enabled: bool


class WebhookResponse(BaseModel):
    id: uuid.UUID
    url: str
    type_keys: list[str]
    enabled: bool
    failure_count: int
    last_failure_at: datetime | None
    created_at: datetime


class WebhookUpdate(BaseModel):
    url: str | None = None
    type_keys: list[str] | None = None
    enabled: bool | None = None
```

In `backend/app/api/v1/notifications.py`, append per-user webhook endpoints (`GET/POST/DELETE/PATCH /webhooks`). Generate `secret` server-side via `secrets.token_urlsafe(32)` on create.

In `backend/app/api/v1/communities.py`, add admin-gated `/communities/{id}/webhooks` CRUD that asserts the calling user has community admin role (use existing role helper). Reject non-admin with `WEBHOOK_FORBIDDEN`.

`backend/tests/integration/api/test_webhooks_api.py`:

```python
"""@file test_webhooks_api.py @brief Webhook CRUD endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_returns_secret_once(client_authed) -> None:
    res = await client_authed.post("/api/v1/notifications/webhooks",
                                   json={"url": "https://example.test/hook",
                                         "type_keys": ["mention"]})
    assert res.status_code == 200
    body = res.json()
    assert body["secret"]  # present on create
    sub_id = body["id"]
    res2 = await client_authed.get("/api/v1/notifications/webhooks")
    listing = res2.json()
    item = next(i for i in listing if i["id"] == sub_id)
    assert "secret" not in item


@pytest.mark.asyncio
async def test_disable_then_enable(client_authed) -> None:
    create = (await client_authed.post(
        "/api/v1/notifications/webhooks",
        json={"url": "https://x.test", "type_keys": []},
    )).json()
    res = await client_authed.patch(
        f"/api/v1/notifications/webhooks/{create['id']}",
        json={"enabled": False},
    )
    assert res.status_code == 200
    listing = (await client_authed.get("/api/v1/notifications/webhooks")).json()
    item = next(i for i in listing if i["id"] == create["id"])
    assert item["enabled"] is False


@pytest.mark.asyncio
async def test_community_webhook_requires_admin(client_authed, community_id) -> None:
    res = await client_authed.post(
        f"/api/v1/communities/{community_id}/webhooks",
        json={"url": "https://comm.test", "type_keys": []},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "WEBHOOK_FORBIDDEN"
```

(Add `client_authed_admin` fixture for the success-path admin test if needed.)

- [ ] **Step 6: Register channel in dispatcher singleton**

In `backend/app/core/dependencies.py`, modify `get_notification_dispatcher()`:

```python
from app.repositories.webhook_repo import WebhookRepository
from app.services.notifications.channels.webhook import WebhookChannel
...
def _webhook_repo_factory():
    # Webhook channel needs a session per call; use the request-scoped session via a
    # newly opened session per delivery (because channel runs inside notify())
    return WebhookRepository(_get_open_session())  # see Note below
```

**Note:** Webhook fanout enqueues Celery tasks but the *list_matching* read needs a session. Keep this synchronous-with-current-request: pass the active `AsyncSession` into the channel via a thread-local request context (`contextvars.ContextVar`). Add `app/core/session_ctx.py` with `current_session: ContextVar[AsyncSession | None]`. Set in `get_db` dependency. `_webhook_repo_factory` reads it.

- [ ] **Step 7: Verify PASS**

```bash
cd backend && pytest tests/unit/repositories/test_webhook_repo.py tests/unit/services/notifications/channels/test_webhook.py tests/integration/api/test_webhooks_api.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/repositories/webhook_repo.py backend/app/services/notifications/channels/webhook.py backend/app/tasks/notification_tasks.py backend/app/schemas/webhook.py backend/app/api/v1/notifications.py backend/app/api/v1/communities.py backend/app/core/dependencies.py backend/app/core/session_ctx.py backend/tests/unit/repositories/test_webhook_repo.py backend/tests/unit/services/notifications/channels/test_webhook.py backend/tests/integration/api/test_webhooks_api.py
git commit -m "feat(notifications): webhook channel + sub CRUD (user + admin)"
```

---

## Task 6: Plan-B smoke

- [ ] **Step 1: Full test suite green**

```bash
cd backend && pytest --cov=app --cov-report=term -q
```
Expected: green; coverage ≥ pre-Plan-B baseline.

- [ ] **Step 2: Migration up + down + up**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

- [ ] **Step 3: Manual smoke**

- Set `dnd_until` 1h ahead → notify mention → verify email/push suppressed in logs, in-app row exists.
- Send 3 reactions on same `target_id` within 10 min → verify single row, `count=3`, `actor_ids` has 3 ids.
- Set `digest_cadence.reaction = "hourly"` → notify reaction → verify row in `notification_digest_queue`, no email sent. After 1h, beat fires `digest_dispatch` → digest email sent.
- Create webhook sub → trigger event → receiver gets HMAC-signed POST. Force receiver to 500 → after retries `failure_count` increments. After 10 failures → `enabled=false`.

- [ ] **Step 4: Commit (any cleanup)**

```bash
git add -A && git diff --cached --quiet || git commit -m "chore(notifications): plan-B smoke + cleanup"
```

---

## Self-Review

- **Spec coverage (Plan B scope):** §6.2/§6.3/§6.4 (DnD/digest/webhook tables) — Task 1; §6.5 (coalescer SQL) — Task 2; §7.1 throttling (push suppression on coalesced row, webhook retry+disable) — Tasks 4 & 5; §7.4 digest dispatch — Task 4; §8 endpoints (`/snooze`, `/preferences` extension, `/webhooks`) — Tasks 3 & 5; §10 errors per-channel isolation — Task 5; §11 metrics / structured logs — emitted in channel `logger.info("notif.dispatched", ...)` from Plan A Task 8.
- **Placeholders:** none in code blocks. Webhook payload's `category` lookup uses dynamic registry import — refactor that one-liner during implementation if the import gets ugly.
- **Type consistency:** `should_send_now(cadence, last_sent_at, now, tz)` consistent. `in_dnd(schedule, until, tz, now)` consistent. `WebhookRepository.list_matching(community_id, user_id, type_key)` consistent across channel + tests.

---

## Execution Handoff

Plan B complete and saved to `docs/superpowers/plans/2026-05-02-notifications-plan-b-smart-delivery.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task
2. **Inline Execution** — executing-plans, batch with checkpoints

Which approach?
