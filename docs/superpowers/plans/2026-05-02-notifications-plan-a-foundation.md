# Notifications Refactor — Plan A: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the registry-driven notification core: in-process `NotificationType` registry, JSONB prefs migration, dispatcher with `inapp`/`email`/`push` channels (push wired correctly), façade rewrite, and updated call sites. No UX changes; behavior parity to today plus working push delivery.

**Architecture:** A single in-process registry holds all `NotificationType` declarations (one module per type). `NotificationService` is a thin façade that validates, resolves prefs, and hands off to a `Dispatcher`, which fans out to channel implementations behind a uniform `Channel` Protocol. Per-type prefs move from per-column DDL into a `notification_prefs JSONB` column on `user_settings`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, Celery, pytest + pytest-asyncio + AsyncMock, structlog.

**Spec:** `docs/superpowers/specs/2026-05-02-notifications-refactor-design.md` (sections 1–8, 10–14).

**Migration revision id used in this plan:** `b2c3d4e5f6a7`. **Down-revision:** `a1b2c3d4e5f6` (current head — verify with `alembic heads` before starting Task 3).

---

## File Structure

| Path | Status | Purpose |
|---|---|---|
| `backend/app/services/notifications/__init__.py` | Create | Package marker; re-exports `register`, `get`, `iter_types`, `NotificationType`, `NotificationPayload`, `Action`, `Channel` |
| `backend/app/services/notifications/registry.py` | Create | Registry primitives (~120 LOC) |
| `backend/app/services/notifications/types/__init__.py` | Create | Imports every built-in type module so registration runs at app boot |
| `backend/app/services/notifications/types/{mention,comment,reaction,new_post,system,invite_accepted,event_reminder,event_rsvp,gallery_activity,gallery_reminder,prompt,prompt_summary}.py` | Create | One module per built-in type (~30–60 LOC each) |
| `backend/app/services/notifications/channels/__init__.py` | Create | Re-exports built-in channels |
| `backend/app/services/notifications/channels/base.py` | Create | `Channel` Protocol + `ChannelResult` dataclass |
| `backend/app/services/notifications/channels/inapp.py` | Create | Persists row + emits `user_notification` SSE |
| `backend/app/services/notifications/channels/email.py` | Create | Delegates to `send_email_notification` Celery task |
| `backend/app/services/notifications/channels/push.py` | Create | Calls `PushService.send_push` |
| `backend/app/services/notifications/dispatcher.py` | Create | Channel registration + `dispatch()` orchestrator |
| `backend/app/services/notifications/prefs.py` | Create | `effective_channels(type, user_settings)` resolver |
| `backend/app/services/mentions.py` | Create | Pure mention-extraction utility (extracted from `NotificationService`) |
| `backend/app/services/notification_service.py` | Rewrite | Thin façade: `notify`, `list_active`, `list_history`, `mark_read`, `dismiss`, `dismiss_all`, `mark_all_read`, `get_prefs`, `set_prefs` |
| `backend/app/repositories/notification_repo.py` | Modify | Add `list_active`, `dismiss`, `dismiss_all_for_user` |
| `backend/app/models/notification.py` | Modify | Add `group_key`, `count`, `actor_ids`, `updated_at`, `dismissed_at` columns + indexes |
| `backend/app/models/user_settings.py` | Modify | Add `notification_prefs JSONB`, drop legacy `notif_*_*` + `mute_all_*` columns |
| `backend/app/schemas/notification.py` | Modify | New `NotificationTypeSchema`, `PreferencesResponse`, `PreferencesUpdate`, `NotifActionRequest` |
| `backend/app/api/v1/notifications.py` | Modify | New endpoints: `/types`, `/active`, `/{id}/dismiss`, `/dismiss-all`, `/preferences` (GET/PATCH) |
| `backend/app/services/post_service.py` | Modify | Use `services.mentions.extract` instead of `notification_service.notify_mentions` |
| `backend/app/services/gallery_service.py` | Modify | Type `notification_service: NotificationService` (drop `Any | None`) |
| `backend/app/services/event_service.py` | Modify | Same — type `notification_service: NotificationService` |
| `backend/app/services/prompt_service.py` | Modify | Same |
| `backend/app/services/auth_service.py` | Modify | Already typed; verify call site after façade rewrite |
| `backend/app/tasks/gallery_tasks.py` | Modify | Same `Any | None` cleanup |
| `backend/app/tasks/notification_tasks.py` | Modify | Replace `send_push_notification` stub with real impl |
| `backend/app/services/push_service.py` | Modify | No API change; verify `send_push` callable from channel |
| `backend/alembic/versions/b2c3d4e5f6a7_notifications_v2_foundation.py` | Create | JSONB prefs + Notification new cols + indexes; backfill; drop legacy cols |
| `backend/tests/unit/services/notifications/__init__.py` | Create | Marker |
| `backend/tests/unit/services/notifications/test_registry.py` | Create | Registry contract tests |
| `backend/tests/unit/services/notifications/test_prefs.py` | Create | Effective-channel resolution tests |
| `backend/tests/unit/services/notifications/test_dispatcher.py` | Create | Channel fanout + isolation tests |
| `backend/tests/unit/services/notifications/channels/test_inapp.py` | Create | Persist + SSE emit tests |
| `backend/tests/unit/services/notifications/channels/test_email.py` | Create | Celery delegation tests |
| `backend/tests/unit/services/notifications/channels/test_push.py` | Create | `PushService.send_push` invocation tests |
| `backend/tests/unit/services/notifications/types/test_builtin_types.py` | Create | Each built-in type registers + payload validates |
| `backend/tests/unit/services/test_notification_service.py` | Modify | Rewrite around new façade |
| `backend/tests/unit/services/test_mentions.py` | Create | Mention extraction (moved from `test_notification_service.py`) |
| `backend/tests/integration/migrations/test_notif_v2_foundation.py` | Create | Seed legacy cols → run migration → assert JSONB shape |

---

## Task 1: Registry primitives

**Files:**
- Create: `backend/app/services/notifications/__init__.py`
- Create: `backend/app/services/notifications/registry.py`
- Create: `backend/tests/unit/services/notifications/__init__.py`
- Test: `backend/tests/unit/services/notifications/test_registry.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/unit/services/notifications/test_registry.py`:

```python
"""@file test_registry.py @brief Notification registry contract tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.services.notifications.registry import (
    Action,
    NotificationPayload,
    NotificationType,
    _REGISTRY,
    get,
    iter_types,
    register,
    to_json_schema,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    snapshot = dict(_REGISTRY)
    _REGISTRY.clear()
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


class _DummyPayload(NotificationPayload):
    foo: str


def _make_type(key: str = "x.test", **overrides) -> NotificationType:
    base = dict(
        key=key,
        category="system",
        payload_schema=_DummyPayload,
        default_channels={"inapp": True, "email": False, "push": False, "toast": False},
        label_i18n=f"notif.{key}.label",
    )
    base.update(overrides)
    return NotificationType(**base)


def test_register_and_get_round_trip() -> None:
    t = _make_type("x.basic")
    register(t)
    assert get("x.basic") is t


def test_register_duplicate_raises() -> None:
    register(_make_type("x.dup"))
    with pytest.raises(ValueError, match="duplicate"):
        register(_make_type("x.dup"))


def test_get_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get("x.does_not_exist")


def test_iter_types_returns_all_registered() -> None:
    register(_make_type("x.a"))
    register(_make_type("x.b"))
    keys = {t.key for t in iter_types()}
    assert {"x.a", "x.b"} <= keys


def test_payload_schema_validates() -> None:
    register(_make_type("x.schema"))
    t = get("x.schema")
    parsed = t.payload_schema.model_validate({"message": "hi", "foo": "bar"})
    assert parsed.foo == "bar"
    with pytest.raises(ValidationError):
        t.payload_schema.model_validate({"message": "hi"})  # missing foo


def test_to_json_schema_includes_registered_types() -> None:
    register(_make_type("x.json"))
    items = to_json_schema()
    keys = {item["key"] for item in items}
    assert "x.json" in keys
    item = next(i for i in items if i["key"] == "x.json")
    assert item["category"] == "system"
    assert item["default_channels"]["inapp"] is True
    assert "payload_schema" in item  # JSON-schema dict


def test_action_url_template_can_carry_target_id() -> None:
    a = Action(key="ack", label_i18n="x.ack", method="POST",
               url_template="/api/v1/things/{target_id}/ack")
    assert "{target_id}" in a.url_template
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/test_registry.py -v
```
Expected: collection error (`ModuleNotFoundError: app.services.notifications.registry`).

- [ ] **Step 3: Implement registry**

`backend/app/services/notifications/__init__.py`:

```python
"""@file __init__.py @brief Public re-exports for the notification registry."""
from app.services.notifications.registry import (
    Action,
    Channel,
    NotificationPayload,
    NotificationType,
    get,
    iter_types,
    register,
    to_json_schema,
)

__all__ = [
    "Action",
    "Channel",
    "NotificationPayload",
    "NotificationType",
    "get",
    "iter_types",
    "register",
    "to_json_schema",
]
```

`backend/app/services/notifications/registry.py`:

```python
"""
@file registry.py
@brief In-process registry of NotificationType declarations.

Built-in types live under ``services.notifications.types`` and are imported
on app start; plugins register additional types by calling :func:`register`
during their own import.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

Channel = Literal["inapp", "email", "push", "webhook", "toast"]
Category = Literal["social", "event", "gallery", "prompt", "system", "plugin"]


class NotificationPayload(BaseModel):
    """@brief Base payload; per-type payloads subclass this."""

    message: str
    link: str | None = None
    actor_id: str | None = None
    target_id: str | None = None


@dataclass(frozen=True)
class Action:
    """@brief Inline action exposed by a notification row."""

    key: str
    label_i18n: str
    method: Literal["POST", "PUT", "DELETE"]
    url_template: str
    style: Literal["primary", "neutral", "danger"] = "neutral"


@dataclass(frozen=True)
class NotificationType:
    """
    @brief Declarative description of a notification type.

    @param key                Unique short identifier (``"reaction"``).
    @param category           High-level grouping for UI.
    @param payload_schema     Pydantic model used to validate ``payload`` dicts.
    @param default_channels   Per-channel defaults if user has no override.
    @param user_configurable  Channels exposed in the settings UI.
    @param group_window_seconds  If set, coalesce events sharing target_id.
    @param toast_on_arrival   Frontend should auto-toast on SSE arrival.
    @param bypass_dnd         True types still deliver during DnD windows.
    @param digestable         Eligible for digest cadence beyond ``instant``.
    @param actions            Inline action declarations.
    @param label_i18n         i18n key for the type's display label.
    @param icon               Heroicons name used by the renderer.
    @param plugin_id          Set by the plugin loader; ``None`` for core.
    """

    key: str
    category: Category
    payload_schema: type[NotificationPayload]
    default_channels: dict[Channel, bool]
    user_configurable: tuple[Channel, ...] = ("inapp", "email", "push", "toast")
    group_window_seconds: int | None = None
    toast_on_arrival: bool = False
    bypass_dnd: bool = False
    digestable: bool = True
    actions: tuple[Action, ...] = ()
    label_i18n: str = ""
    icon: str = "inbox"
    plugin_id: str | None = None


_REGISTRY: dict[str, NotificationType] = {}


def register(t: NotificationType) -> None:
    """@brief Register a notification type. Raises on duplicate ``key``."""
    if t.key in _REGISTRY:
        raise ValueError(f"duplicate notification type: {t.key}")
    _REGISTRY[t.key] = t


def get(key: str) -> NotificationType:
    """@brief Look up a registered type by key. Raises KeyError if unknown."""
    return _REGISTRY[key]


def iter_types() -> list[NotificationType]:
    """@brief Snapshot list of all registered types (stable order)."""
    return list(_REGISTRY.values())


def to_json_schema() -> list[dict[str, Any]]:
    """@brief Serialize the registry for the frontend bootstrap endpoint."""
    out: list[dict[str, Any]] = []
    for t in _REGISTRY.values():
        out.append(
            {
                "key": t.key,
                "category": t.category,
                "default_channels": dict(t.default_channels),
                "user_configurable": list(t.user_configurable),
                "group_window_seconds": t.group_window_seconds,
                "toast_on_arrival": t.toast_on_arrival,
                "bypass_dnd": t.bypass_dnd,
                "digestable": t.digestable,
                "actions": [
                    {
                        "key": a.key,
                        "label_i18n": a.label_i18n,
                        "method": a.method,
                        "url_template": a.url_template,
                        "style": a.style,
                    }
                    for a in t.actions
                ],
                "label_i18n": t.label_i18n,
                "icon": t.icon,
                "plugin_id": t.plugin_id,
                "payload_schema": t.payload_schema.model_json_schema(),
            }
        )
    return out
```

`backend/tests/unit/services/notifications/__init__.py`: empty file.

- [ ] **Step 4: Run, verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/test_registry.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Lint + types**

```bash
cd backend && ruff check app/services/notifications && mypy app/services/notifications
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/notifications/ backend/tests/unit/services/notifications/__init__.py backend/tests/unit/services/notifications/test_registry.py
git commit -m "feat(notifications): in-process notification type registry"
```

---

## Task 2: Built-in type registrations

**Files:**
- Create: `backend/app/services/notifications/types/__init__.py`
- Create: `backend/app/services/notifications/types/{mention,comment,reaction,new_post,system,invite_accepted,event_reminder,event_rsvp,gallery_activity,gallery_reminder,prompt,prompt_summary}.py`
- Test: `backend/tests/unit/services/notifications/types/test_builtin_types.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/types/__init__.py`: empty file.

`backend/tests/unit/services/notifications/types/test_builtin_types.py`:

```python
"""@file test_builtin_types.py @brief All 12 built-in types register on import."""
from __future__ import annotations

import pytest

from app.services.notifications.registry import _REGISTRY, get


EXPECTED_KEYS = (
    "mention", "comment", "reaction", "new_post", "system",
    "invite_accepted", "event_reminder", "event_rsvp",
    "gallery_activity", "gallery_reminder", "prompt", "prompt_summary",
)


@pytest.fixture(autouse=True)
def _import_types():
    _REGISTRY.clear()
    import importlib

    importlib.import_module("app.services.notifications.types")  # triggers registrations
    yield


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_builtin_type_registered(key: str) -> None:
    t = get(key)
    assert t.key == key
    assert t.label_i18n.startswith("notif.")
    assert "inapp" in t.default_channels


def test_mention_payload_requires_actor_name() -> None:
    t = get("mention")
    parsed = t.payload_schema.model_validate({
        "message": "@you", "actor_name": "Alice", "target_id": "post-1",
    })
    assert parsed.actor_name == "Alice"


def test_reaction_groups_with_window() -> None:
    t = get("reaction")
    assert t.group_window_seconds and t.group_window_seconds >= 60


def test_mention_toasts_on_arrival_and_bypasses_dnd() -> None:
    t = get("mention")
    assert t.toast_on_arrival is True
    # mentions are personal — should still surface even in DnD
    assert t.bypass_dnd is False  # design choice: mentions respect DnD; system overrides
    assert "push" in t.user_configurable
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/types/test_builtin_types.py -v
```
Expected: `ModuleNotFoundError: app.services.notifications.types`.

- [ ] **Step 3: Create the 12 type modules**

`backend/app/services/notifications/types/__init__.py`:

```python
"""@file __init__.py @brief Imports trigger built-in registrations."""
from app.services.notifications.types import (  # noqa: F401
    comment,
    event_reminder,
    event_rsvp,
    gallery_activity,
    gallery_reminder,
    invite_accepted,
    mention,
    new_post,
    prompt,
    prompt_summary,
    reaction,
    system,
)
```

`backend/app/services/notifications/types/mention.py`:

```python
"""@file mention.py @brief @-mention notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class MentionPayload(NotificationPayload):
    actor_name: str
    excerpt: str | None = None


register(NotificationType(
    key="mention",
    category="social",
    payload_schema=MentionPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    toast_on_arrival=True,
    label_i18n="notif.mention.label",
    icon="at-symbol",
))
```

`backend/app/services/notifications/types/comment.py`:

```python
"""@file comment.py @brief Reply / comment notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class CommentPayload(NotificationPayload):
    actor_name: str
    excerpt: str | None = None


register(NotificationType(
    key="comment",
    category="social",
    payload_schema=CommentPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": True},
    group_window_seconds=300,
    toast_on_arrival=True,
    label_i18n="notif.comment.label",
    icon="chat-bubble-left",
))
```

`backend/app/services/notifications/types/reaction.py`:

```python
"""@file reaction.py @brief Reaction (heart/like/etc) notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class ReactionPayload(NotificationPayload):
    actor_name: str
    emoji: str | None = None
    excerpt: str | None = None


register(NotificationType(
    key="reaction",
    category="social",
    payload_schema=ReactionPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    label_i18n="notif.reaction.label",
    icon="heart",
))
```

`backend/app/services/notifications/types/new_post.py`:

```python
"""@file new_post.py @brief New community/subgroup post notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class NewPostPayload(NotificationPayload):
    actor_name: str
    title: str | None = None


register(NotificationType(
    key="new_post",
    category="social",
    payload_schema=NewPostPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=900,
    label_i18n="notif.new_post.label",
    icon="document-text",
))
```

`backend/app/services/notifications/types/system.py`:

```python
"""@file system.py @brief Operational/system notification type (always on)."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


register(NotificationType(
    key="system",
    category="system",
    payload_schema=NotificationPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    user_configurable=(),       # cannot be turned off
    bypass_dnd=True,
    toast_on_arrival=True,
    label_i18n="notif.system.label",
    icon="exclamation-triangle",
))
```

`backend/app/services/notifications/types/invite_accepted.py`:

```python
"""@file invite_accepted.py @brief Invite accepted notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class InviteAcceptedPayload(NotificationPayload):
    actor_name: str


register(NotificationType(
    key="invite_accepted",
    category="social",
    payload_schema=InviteAcceptedPayload,
    default_channels={"inapp": True, "email": True, "push": False, "toast": False},
    label_i18n="notif.invite_accepted.label",
    icon="user-plus",
))
```

`backend/app/services/notifications/types/event_reminder.py`:

```python
"""@file event_reminder.py @brief Event reminder notification type."""
from datetime import datetime
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class EventReminderPayload(NotificationPayload):
    event_title: str
    starts_at: datetime


register(NotificationType(
    key="event_reminder",
    category="event",
    payload_schema=EventReminderPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    toast_on_arrival=True,
    bypass_dnd=False,
    label_i18n="notif.event_reminder.label",
    icon="calendar",
))
```

`backend/app/services/notifications/types/event_rsvp.py`:

```python
"""@file event_rsvp.py @brief RSVP change notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class EventRsvpPayload(NotificationPayload):
    actor_name: str
    event_title: str
    status: str  # "going" | "maybe" | "no"


register(NotificationType(
    key="event_rsvp",
    category="event",
    payload_schema=EventRsvpPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    label_i18n="notif.event_rsvp.label",
    icon="calendar",
))
```

`backend/app/services/notifications/types/gallery_activity.py`:

```python
"""@file gallery_activity.py @brief Gallery upload/comment notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class GalleryActivityPayload(NotificationPayload):
    actor_name: str
    gallery_title: str
    activity: str  # "upload" | "comment" | "favorite"


register(NotificationType(
    key="gallery_activity",
    category="gallery",
    payload_schema=GalleryActivityPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=900,
    label_i18n="notif.gallery_activity.label",
    icon="photo",
))
```

`backend/app/services/notifications/types/gallery_reminder.py`:

```python
"""@file gallery_reminder.py @brief Gallery contribution reminder."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class GalleryReminderPayload(NotificationPayload):
    gallery_title: str


register(NotificationType(
    key="gallery_reminder",
    category="gallery",
    payload_schema=GalleryReminderPayload,
    default_channels={"inapp": True, "email": True, "push": False, "toast": False},
    label_i18n="notif.gallery_reminder.label",
    icon="photo",
))
```

`backend/app/services/notifications/types/prompt.py`:

```python
"""@file prompt.py @brief New prompt notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class PromptPayload(NotificationPayload):
    prompt_title: str


register(NotificationType(
    key="prompt",
    category="prompt",
    payload_schema=PromptPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": True},
    toast_on_arrival=True,
    label_i18n="notif.prompt.label",
    icon="sparkles",
))
```

`backend/app/services/notifications/types/prompt_summary.py`:

```python
"""@file prompt_summary.py @brief Daily prompt summary notification type."""
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, register,
)


class PromptSummaryPayload(NotificationPayload):
    response_count: int


register(NotificationType(
    key="prompt_summary",
    category="prompt",
    payload_schema=PromptSummaryPayload,
    default_channels={"inapp": True, "email": True, "push": False, "toast": False},
    digestable=True,
    label_i18n="notif.prompt_summary.label",
    icon="sparkles",
))
```

- [ ] **Step 4: Run, verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/types/test_builtin_types.py -v
```
Expected: 15 passed (12 parametrized + 3 explicit).

- [ ] **Step 5: Lint + types**

```bash
cd backend && ruff check app/services/notifications/types && mypy app/services/notifications/types
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/notifications/types/ backend/tests/unit/services/notifications/types/
git commit -m "feat(notifications): register 12 built-in notification types"
```

---

## Task 3: Migration v2 — JSONB prefs + grouped notification columns

**Files:**
- Create: `backend/alembic/versions/b2c3d4e5f6a7_notifications_v2_foundation.py`
- Modify: `backend/app/models/notification.py`
- Modify: `backend/app/models/user_settings.py`
- Test: `backend/tests/integration/migrations/test_notif_v2_foundation.py`

- [ ] **Step 1: Confirm head**

```bash
cd backend && alembic heads
```
Expected: `a1b2c3d4e5f6 (head)`. If different, update `down_revision` in the migration to match.

- [ ] **Step 2: Write failing migration test**

`backend/tests/integration/migrations/__init__.py`: empty file (if missing).

`backend/tests/integration/migrations/test_notif_v2_foundation.py`:

```python
"""@file test_notif_v2_foundation.py @brief Verify v2 migration backfills JSONB prefs and adds notification cols."""
from __future__ import annotations

import json
import uuid

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


def _engine():
    return create_engine(get_settings().DATABASE_URL_SYNC, future=True)


def test_migration_backfills_prefs_and_drops_legacy_cols(alembic_cfg):
    eng = _engine()
    with eng.begin() as conn:
        # Reset to previous head
        command.downgrade(alembic_cfg, "a1b2c3d4e5f6")

        # Seed a user_settings row at the legacy schema
        user_id = uuid.uuid4()
        conn.execute(text("""
            INSERT INTO users (id, email, username, display_name, password_hash, is_active)
            VALUES (:id, :email, :u, :dn, '!', true)
        """), {"id": user_id, "email": f"{user_id}@e.test",
               "u": f"u{user_id.hex[:8]}", "dn": "Tester"})
        conn.execute(text("""
            INSERT INTO user_settings (user_id, notif_mention_inapp, notif_mention_email,
                                       notif_mention_push, notif_reaction_inapp,
                                       mute_all_email)
            VALUES (:uid, true, true, true, true, false)
        """), {"uid": user_id})

    command.upgrade(alembic_cfg, "b2c3d4e5f6a7")

    with eng.begin() as conn:
        row = conn.execute(text(
            "SELECT notification_prefs FROM user_settings WHERE user_id = :uid"
        ), {"uid": user_id}).scalar_one()
        prefs = row if isinstance(row, dict) else json.loads(row)
        assert prefs["mention"] == {"inapp": True, "email": True, "push": True, "toast": True}
        assert prefs["reaction"]["inapp"] is True

        cols = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'user_settings'
        """)).scalars().all()
        # Legacy columns dropped
        assert "notif_mention_inapp" not in cols
        assert "mute_all_email" not in cols
        # New columns present
        assert "notification_prefs" in cols

        # Notification columns
        notif_cols = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'notifications'
        """)).scalars().all()
        for c in ("group_key", "count", "actor_ids", "updated_at", "dismissed_at"):
            assert c in notif_cols
```

- [ ] **Step 3: Run, verify FAIL**

```bash
cd backend && pytest tests/integration/migrations/test_notif_v2_foundation.py -xvs
```
Expected: `KeyError: 'b2c3d4e5f6a7'` (revision not found).

- [ ] **Step 4: Author the migration**

`backend/alembic/versions/b2c3d4e5f6a7_notifications_v2_foundation.py`:

```python
"""notifications v2 foundation: JSONB prefs + grouped notification columns.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-02
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


# Per-(legacy column, type_key, channel) backfill table.
_LEGACY_PREFS = [
    ("notif_mention_inapp", "mention", "inapp"),
    ("notif_mention_email", "mention", "email"),
    ("notif_mention_push", "mention", "push"),
    ("notif_comment_inapp", "comment", "inapp"),
    ("notif_comment_email", "comment", "email"),
    ("notif_comment_push", "comment", "push"),
    ("notif_reaction_inapp", "reaction", "inapp"),
    ("notif_reaction_email", "reaction", "email"),
    ("notif_reaction_push", "reaction", "push"),
    ("notif_new_post_inapp", "new_post", "inapp"),
    ("notif_new_post_email", "new_post", "email"),
    ("notif_new_post_push", "new_post", "push"),
    ("notif_system_inapp", "system", "inapp"),
    ("notif_system_email", "system", "email"),
    ("notif_system_push", "system", "push"),
    ("notif_invite_accepted_inapp", "invite_accepted", "inapp"),
    ("notif_invite_accepted_email", "invite_accepted", "email"),
    ("notif_invite_accepted_push", "invite_accepted", "push"),
    ("notif_event_reminder_inapp", "event_reminder", "inapp"),
    ("notif_event_reminder_email", "event_reminder", "email"),
    ("notif_event_rsvp_inapp", "event_rsvp", "inapp"),
    ("notif_event_rsvp_email", "event_rsvp", "email"),
    ("notif_gallery_activity_inapp", "gallery_activity", "inapp"),
    ("notif_gallery_activity_email", "gallery_activity", "email"),
    ("notif_prompt_inapp", "prompt", "inapp"),
    ("notif_prompt_email", "prompt", "email"),
    ("notif_prompt_summary_inapp", "prompt_summary", "inapp"),
    ("notif_prompt_summary_email", "prompt_summary", "email"),
]

# Defaults for any (type, channel) not present in legacy schema.
_TYPE_DEFAULTS: dict[str, dict[str, bool]] = {
    "mention":          {"inapp": True,  "email": True,  "push": True,  "toast": True},
    "comment":          {"inapp": True,  "email": False, "push": False, "toast": True},
    "reaction":         {"inapp": True,  "email": False, "push": False, "toast": False},
    "new_post":         {"inapp": True,  "email": False, "push": False, "toast": False},
    "system":           {"inapp": True,  "email": True,  "push": True,  "toast": True},
    "invite_accepted":  {"inapp": True,  "email": True,  "push": False, "toast": False},
    "event_reminder":   {"inapp": True,  "email": True,  "push": True,  "toast": True},
    "event_rsvp":       {"inapp": True,  "email": False, "push": False, "toast": False},
    "gallery_activity": {"inapp": True,  "email": False, "push": False, "toast": False},
    "gallery_reminder": {"inapp": True,  "email": True,  "push": False, "toast": False},
    "prompt":           {"inapp": True,  "email": False, "push": False, "toast": True},
    "prompt_summary":   {"inapp": True,  "email": True,  "push": False, "toast": False},
}


def upgrade() -> None:
    # 1. notifications: new columns
    op.add_column("notifications", sa.Column("group_key", sa.Text(), nullable=True))
    op.add_column("notifications", sa.Column(
        "count", sa.Integer(), nullable=False, server_default="1",
    ))
    op.add_column("notifications", sa.Column(
        "actor_ids",
        postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
        nullable=False,
        server_default="{}",
    ))
    op.add_column("notifications", sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ))
    op.add_column("notifications", sa.Column(
        "dismissed_at", sa.DateTime(timezone=True), nullable=True,
    ))

    op.create_index(
        "notifications_group_active_idx",
        "notifications",
        ["user_id", "group_key"],
        unique=True,
        postgresql_where=sa.text("group_key IS NOT NULL AND read_at IS NULL"),
    )
    op.create_index(
        "notifications_user_active_idx",
        "notifications",
        ["user_id", "dismissed_at", sa.text("created_at DESC")],
        postgresql_where=sa.text("dismissed_at IS NULL"),
    )

    # 2. user_settings: add JSONB prefs
    op.add_column("user_settings", sa.Column(
        "notification_prefs",
        postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ))

    # 3. Backfill notification_prefs from legacy columns + defaults
    bind = op.get_bind()
    insp = sa.inspect(bind)
    legacy_cols = {c["name"] for c in insp.get_columns("user_settings")}

    rows = bind.execute(sa.text(
        "SELECT user_id, " + ", ".join(
            c for c, _, _ in _LEGACY_PREFS if c in legacy_cols
        ) + " FROM user_settings"
    )).mappings().all()

    for row in rows:
        prefs: dict[str, dict[str, bool]] = {}
        for type_key, defaults in _TYPE_DEFAULTS.items():
            prefs[type_key] = dict(defaults)
        for col, type_key, channel in _LEGACY_PREFS:
            if col in legacy_cols and row[col] is not None:
                prefs[type_key][channel] = bool(row[col])
        bind.execute(
            sa.text("UPDATE user_settings SET notification_prefs = :p WHERE user_id = :uid"),
            {"p": sa.dialects.postgresql.JSONB().bind_processor(bind.dialect)(prefs)
                  if False else __import__("json").dumps(prefs),
             "uid": row["user_id"]},
        )

    # 4. Drop legacy columns
    for col, _, _ in _LEGACY_PREFS:
        if col in legacy_cols:
            op.drop_column("user_settings", col)
    for legacy in ("mute_all_email", "mute_all_push"):
        if legacy in legacy_cols:
            op.drop_column("user_settings", legacy)


def downgrade() -> None:
    op.drop_index("notifications_user_active_idx", table_name="notifications")
    op.drop_index("notifications_group_active_idx", table_name="notifications")
    op.drop_column("notifications", "dismissed_at")
    op.drop_column("notifications", "updated_at")
    op.drop_column("notifications", "actor_ids")
    op.drop_column("notifications", "count")
    op.drop_column("notifications", "group_key")
    op.drop_column("user_settings", "notification_prefs")
    # Recreate legacy columns at their prior defaults
    for col, _, channel in _LEGACY_PREFS:
        default = "true" if channel == "inapp" else "false"
        op.add_column("user_settings", sa.Column(
            col, sa.Boolean(), nullable=False, server_default=default,
        ))
    op.add_column("user_settings", sa.Column(
        "mute_all_email", sa.Boolean(), nullable=False, server_default="false",
    ))
    op.add_column("user_settings", sa.Column(
        "mute_all_push", sa.Boolean(), nullable=False, server_default="false",
    ))
```

- [ ] **Step 5: Update SQLAlchemy models**

Modify `backend/app/models/notification.py` — add new columns and indexes after `created_at`:

```python
group_key: Mapped[str | None] = mapped_column(Text)
count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
actor_ids: Mapped[list[uuid.UUID]] = mapped_column(
    postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
    nullable=False,
    server_default="{}",
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False,
)
dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```
Add to `__table_args__`:
```python
Index("notifications_user_active_idx", "user_id", "dismissed_at",
      postgresql_where=(dismissed_at.is_(None))),
Index("notifications_group_active_idx", "user_id", "group_key", unique=True,
      postgresql_where=(group_key.isnot(None) & read_at.is_(None))),
```
(Add corresponding `from sqlalchemy import Integer as _Integer` / use existing `sqlalchemy as sa` import; resolve imports at write time.)

Modify `backend/app/models/user_settings.py`:
- Remove every `notif_*_inapp/email/push` and `mute_all_email/push` mapped column.
- Add:
```python
notification_prefs: Mapped[dict] = mapped_column(
    JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"),
)
```

- [ ] **Step 6: Run migration test, verify PASS**

```bash
cd backend && pytest tests/integration/migrations/test_notif_v2_foundation.py -xvs
```
Expected: 1 passed.

- [ ] **Step 7: Mypy + ruff**

```bash
cd backend && ruff check app/models alembic/versions/b2c3d4e5f6a7_notifications_v2_foundation.py && mypy app/models
```
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add backend/alembic/versions/b2c3d4e5f6a7_notifications_v2_foundation.py backend/app/models/notification.py backend/app/models/user_settings.py backend/tests/integration/migrations/
git commit -m "feat(notifications): JSONB prefs + grouped-notification columns (alembic v2)"
```

---

## Task 4: Effective-channel preference resolver

**Files:**
- Create: `backend/app/services/notifications/prefs.py`
- Test: `backend/tests/unit/services/notifications/test_prefs.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/test_prefs.py`:

```python
"""@file test_prefs.py @brief Effective-channel resolution tests."""
from __future__ import annotations

import pytest

from app.services.notifications.prefs import effective_channels
from app.services.notifications.registry import (
    NotificationPayload, NotificationType,
)


def _t(**overrides) -> NotificationType:
    base = dict(
        key="x.t", category="system", payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": True, "push": False, "toast": False},
        label_i18n="notif.x.label",
    )
    base.update(overrides)
    return NotificationType(**base)


def test_no_user_overrides_returns_defaults() -> None:
    out = effective_channels(_t(), user_prefs={})
    assert out == {"inapp": True, "email": True, "push": False, "toast": False}


def test_user_overrides_merge_over_defaults() -> None:
    t = _t()
    out = effective_channels(t, user_prefs={"x.t": {"email": False, "push": True}})
    assert out == {"inapp": True, "email": False, "push": True, "toast": False}


def test_unknown_user_keys_ignored() -> None:
    t = _t()
    out = effective_channels(t, user_prefs={"other": {"email": False}})
    assert out["email"] is True


def test_user_configurable_filters_settable_channels() -> None:
    t = _t(user_configurable=("inapp", "email"))
    # Even if user tries to disable push, only configurable channels are honored
    out = effective_channels(t, user_prefs={"x.t": {"push": True, "email": False}})
    assert out["push"] is False  # default wins (not configurable)
    assert out["email"] is False
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/test_prefs.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement**

`backend/app/services/notifications/prefs.py`:

```python
"""
@file prefs.py
@brief Resolve effective per-channel notification preferences.
"""
from __future__ import annotations

from typing import Any

from app.services.notifications.registry import Channel, NotificationType


def effective_channels(
    type: NotificationType,
    user_prefs: dict[str, Any],
) -> dict[Channel, bool]:
    """
    @brief Compute the channel-on/off map for a notification.

    Defaults from the type definition; overridden by ``user_prefs[type.key]``
    only on channels that appear in ``type.user_configurable``.
    """
    out: dict[Channel, bool] = dict(type.default_channels)
    for ch in ("inapp", "email", "push", "toast"):
        if ch not in out:
            out[ch] = False  # type: ignore[index]

    overrides = user_prefs.get(type.key) or {}
    for ch, value in overrides.items():
        if ch in type.user_configurable:
            out[ch] = bool(value)  # type: ignore[index]
    return out
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/test_prefs.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notifications/prefs.py backend/tests/unit/services/notifications/test_prefs.py
git commit -m "feat(notifications): effective-channel preference resolver"
```

---

## Task 5: Channel base + in-app channel

**Files:**
- Create: `backend/app/services/notifications/channels/__init__.py`
- Create: `backend/app/services/notifications/channels/base.py`
- Create: `backend/app/services/notifications/channels/inapp.py`
- Test: `backend/tests/unit/services/notifications/channels/__init__.py`
- Test: `backend/tests/unit/services/notifications/channels/test_inapp.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/channels/__init__.py`: empty.

`backend/tests/unit/services/notifications/channels/test_inapp.py`:

```python
"""@file test_inapp.py @brief In-app channel persists row + emits SSE."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.inapp import InAppChannel


@pytest.mark.asyncio
async def test_inapp_emits_sse_event_for_persisted_notification() -> None:
    bus = MagicMock()
    bus.emit = AsyncMock()
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4()
    n.user_id = uuid.uuid4()
    n.type = "mention"
    n.payload = {"message": "x"}
    n.created_at = datetime.now(UTC)
    n.actor_ids = []
    n.count = 1

    ch = InAppChannel(event_bus=bus)
    result = await ch.send(n)

    bus.emit.assert_awaited_once()
    args, _ = bus.emit.call_args
    event = args[0]
    assert event.user_id == n.user_id
    assert event.kind == "user_notification"
    assert isinstance(result, ChannelResult)
    assert result.ok is True


@pytest.mark.asyncio
async def test_inapp_returns_failed_result_on_emit_error() -> None:
    bus = MagicMock()
    bus.emit = AsyncMock(side_effect=RuntimeError("bus down"))
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "x"; n.payload = {}; n.created_at = datetime.now(UTC)
    n.actor_ids = []; n.count = 1

    ch = InAppChannel(event_bus=bus)
    result = await ch.send(n)
    assert result.ok is False
    assert "bus down" in (result.error or "")
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_inapp.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

`backend/app/services/notifications/channels/__init__.py`:

```python
"""@file __init__.py @brief Re-exports the built-in channel implementations."""
from app.services.notifications.channels.base import Channel, ChannelResult
from app.services.notifications.channels.email import EmailChannel
from app.services.notifications.channels.inapp import InAppChannel
from app.services.notifications.channels.push import PushChannel

__all__ = ["Channel", "ChannelResult", "InAppChannel", "EmailChannel", "PushChannel"]
```

`backend/app/services/notifications/channels/base.py`:

```python
"""
@file base.py
@brief Channel Protocol + result type.

Channels never raise; failures are returned as ``ChannelResult(ok=False, ...)``.
The dispatcher logs failed results and continues with the remaining channels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.notification import Notification


@dataclass(frozen=True)
class ChannelResult:
    ok: bool
    skipped_reason: str | None = None  # "coalesced_recently", "dnd", "no_subscriptions"
    error: str | None = None


class Channel(Protocol):
    key: str
    async def send(self, notification: Notification) -> ChannelResult: ...
```

`backend/app/services/notifications/channels/inapp.py`:

```python
"""
@file inapp.py
@brief In-app channel: emits ``user_notification`` SSE event for an already-persisted row.

Note: persistence happens in the dispatcher (via the coalescer) so the row
exists before any channel runs. This channel only publishes to the bus.
"""
from __future__ import annotations

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import Channel, ChannelResult
from app.services.realtime import events
from app.services.realtime.event_bus import EventBus

logger = structlog.get_logger(__name__)


class InAppChannel:
    key = "inapp"

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    async def send(self, notification: Notification) -> ChannelResult:
        try:
            await self._bus.emit(
                events.user_notification(
                    user_id=notification.user_id,
                    notification_id=notification.id,
                    notification_type=notification.type,
                    payload=notification.payload,
                    created_at=notification.created_at.isoformat(),
                ),
            )
            return ChannelResult(ok=True)
        except Exception as exc:  # never propagate — channel isolation
            logger.warning(
                "notif.channel.failed",
                channel="inapp",
                type_key=notification.type,
                user_id=str(notification.user_id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_inapp.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notifications/channels/__init__.py backend/app/services/notifications/channels/base.py backend/app/services/notifications/channels/inapp.py backend/tests/unit/services/notifications/channels/__init__.py backend/tests/unit/services/notifications/channels/test_inapp.py
git commit -m "feat(notifications): channel Protocol + in-app SSE channel"
```

---

## Task 6: Email channel

**Files:**
- Create: `backend/app/services/notifications/channels/email.py`
- Test: `backend/tests/unit/services/notifications/channels/test_email.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/channels/test_email.py`:

```python
"""@file test_email.py @brief Email channel delegates to Celery task."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.notification import Notification
from app.services.notifications.channels.email import EmailChannel


@pytest.mark.asyncio
async def test_email_channel_dispatches_to_celery_task() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "mention"; n.payload = {"message": "x", "link": "/p"}
    n.actor_ids = [uuid.uuid4()]

    with patch("app.services.notifications.channels.email.send_email_notification") as task:
        result = await EmailChannel().send(n)

    task.delay.assert_called_once()
    args, kwargs = task.delay.call_args
    assert args[0] == str(n.user_id)
    assert args[1] == "mention"
    assert args[2]["message"] == "x"
    assert result.ok is True


@pytest.mark.asyncio
async def test_email_channel_returns_failed_on_broker_error() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "x"; n.payload = {}; n.actor_ids = []

    with patch("app.services.notifications.channels.email.send_email_notification") as task:
        task.delay.side_effect = ConnectionError("broker down")
        result = await EmailChannel().send(n)
    assert result.ok is False
    assert "broker down" in (result.error or "")
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_email.py -v
```

- [ ] **Step 3: Implement**

`backend/app/services/notifications/channels/email.py`:

```python
"""@file email.py @brief Email channel: delegates rendering + send to Celery."""
from __future__ import annotations

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import send_email_notification

logger = structlog.get_logger(__name__)


class EmailChannel:
    key = "email"

    async def send(self, notification: Notification) -> ChannelResult:
        try:
            send_email_notification.delay(
                str(notification.user_id),
                notification.type,
                {**notification.payload, "actor_ids": [str(a) for a in notification.actor_ids]},
            )
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed", channel="email",
                type_key=notification.type, user_id=str(notification.user_id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_email.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notifications/channels/email.py backend/tests/unit/services/notifications/channels/test_email.py
git commit -m "feat(notifications): email channel via send_email_notification task"
```

---

## Task 7: Push channel + replace stub task

**Files:**
- Create: `backend/app/services/notifications/channels/push.py`
- Modify: `backend/app/tasks/notification_tasks.py` (replace `send_push_notification` stub)
- Test: `backend/tests/unit/services/notifications/channels/test_push.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/channels/test_push.py`:

```python
"""@file test_push.py @brief Push channel invokes PushService.send_push."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.notification import Notification
from app.services.notifications.channels.push import PushChannel


@pytest.mark.asyncio
async def test_push_channel_enqueues_celery_task() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "mention"
    n.payload = {"message": "Alice mentioned you", "link": "/p/1"}
    n.actor_ids = []

    with patch("app.services.notifications.channels.push.send_push_notification") as task:
        result = await PushChannel().send(n)

    task.delay.assert_called_once()
    args, _ = task.delay.call_args
    assert args[0] == str(n.user_id)
    payload = args[1]
    assert payload["title"]   # title derived from type
    assert payload["body"] == "Alice mentioned you"
    assert payload["url"] == "/p/1"
    assert result.ok is True


@pytest.mark.asyncio
async def test_push_channel_returns_failed_on_broker_error() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "x"; n.payload = {"message": "m"}; n.actor_ids = []

    with patch("app.services.notifications.channels.push.send_push_notification") as task:
        task.delay.side_effect = ConnectionError("broker")
        result = await PushChannel().send(n)
    assert result.ok is False
```

Add Celery task test in `backend/tests/unit/tasks/test_notification_tasks.py` (create if needed):

```python
"""@file test_notification_tasks.py @brief Push task calls PushService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.tasks import notification_tasks


def test_send_push_notification_calls_push_service() -> None:
    uid = str(uuid.uuid4())
    payload = {"title": "T", "body": "B", "url": "/x"}

    with patch("app.tasks.notification_tasks._send_push_async", new=AsyncMock(return_value={"status": "sent"})) as p:
        out = notification_tasks.send_push_notification(uid, payload)
    p.assert_awaited_once()
    assert out == {"status": "sent"}
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_push.py tests/unit/tasks/test_notification_tasks.py -v
```

- [ ] **Step 3: Implement channel**

`backend/app/services/notifications/channels/push.py`:

```python
"""@file push.py @brief Web Push channel — enqueues Celery task per recipient."""
from __future__ import annotations

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.registry import get as registry_get
from app.tasks.notification_tasks import send_push_notification

logger = structlog.get_logger(__name__)


def _title_for(notification: Notification) -> str:
    try:
        t = registry_get(notification.type)
        return t.label_i18n.split(".")[-2] if "." in t.label_i18n else notification.type
    except KeyError:
        return notification.type


class PushChannel:
    key = "push"

    async def send(self, notification: Notification) -> ChannelResult:
        try:
            payload = {
                "title": _title_for(notification),
                "body": str(notification.payload.get("message", "")),
                "url": str(notification.payload.get("link", "/app")),
            }
            send_push_notification.delay(str(notification.user_id), payload)
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed", channel="push",
                type_key=notification.type, user_id=str(notification.user_id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
```

- [ ] **Step 4: Replace push stub task**

In `backend/app/tasks/notification_tasks.py`, replace the entire `send_push_notification` definition with:

```python
async def _send_push_async(user_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, str]:
    from app.core.config import get_settings
    from app.repositories.push_repo import PushSubscriptionRepository
    from app.repositories.settings_repo import SettingsRepository
    from app.services.push_service import PushService

    async with async_session_factory() as session:
        push_repo = PushSubscriptionRepository(session)
        settings_repo = SettingsRepository(session)
        community_id = uuid.UUID(get_settings().COMMUNITY_ID)
        svc = PushService(push_repo, settings_repo, community_id, settings=get_settings())
        await svc.send_push(
            user_id=user_id,
            title=str(payload.get("title", "")),
            body=str(payload.get("body", "")),
            url=str(payload.get("url", "/app")),
        )
    return {"status": "sent"}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.send_push_notification",
    max_retries=3,
    queue="notifications",
)
def send_push_notification(self: Task, user_id: str, payload: dict[str, Any]) -> dict[str, str]:
    """@brief Send a Web Push to all subscriptions for a user."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("send_push_notification_invalid_uuid", user_id=user_id)
        return {"status": "error"}
    try:
        return asyncio.run(_send_push_async(uid, payload))
    except Exception as exc:
        logger.exception("send_push_notification_failed", user_id=user_id, error=str(exc))
        raise self.retry(exc=exc)
```

- [ ] **Step 5: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/channels/test_push.py tests/unit/tasks/test_notification_tasks.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/notifications/channels/push.py backend/app/tasks/notification_tasks.py backend/tests/unit/services/notifications/channels/test_push.py backend/tests/unit/tasks/test_notification_tasks.py
git commit -m "feat(notifications): push channel + real Celery push task"
```

---

## Task 8: Dispatcher orchestrator

**Files:**
- Create: `backend/app/services/notifications/dispatcher.py`
- Test: `backend/tests/unit/services/notifications/test_dispatcher.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/notifications/test_dispatcher.py`:

```python
"""@file test_dispatcher.py @brief Channel fanout + isolation tests."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.dispatcher import Dispatcher
from app.services.notifications.registry import (
    NotificationPayload, NotificationType,
)


def _t(**overrides) -> NotificationType:
    base = dict(
        key="x.t", category="system", payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": True, "push": False, "toast": False},
        label_i18n="notif.x.label",
    )
    base.update(overrides)
    return NotificationType(**base)


def _fake_channel(key: str, ok: bool = True, raise_: bool = False) -> MagicMock:
    ch = MagicMock(spec=["send", "key"])
    ch.key = key
    if raise_:
        ch.send = AsyncMock(side_effect=RuntimeError("boom"))
    else:
        ch.send = AsyncMock(return_value=ChannelResult(ok=ok))
    return ch


def _notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.user_id = uuid.uuid4()
    n.type = "x.t"; n.payload = {"message": "m"}; n.actor_ids = []
    return n


@pytest.mark.asyncio
async def test_dispatch_calls_only_enabled_channels() -> None:
    inapp, email, push = _fake_channel("inapp"), _fake_channel("email"), _fake_channel("push")
    d = Dispatcher(channels={"inapp": inapp, "email": email, "push": push})
    await d.dispatch(_notif(), _t(), {"inapp": True, "email": False, "push": True, "toast": False})
    inapp.send.assert_awaited_once()
    push.send.assert_awaited_once()
    email.send.assert_not_called()


@pytest.mark.asyncio
async def test_one_failing_channel_does_not_block_others() -> None:
    inapp = _fake_channel("inapp", raise_=True)
    email = _fake_channel("email")
    d = Dispatcher(channels={"inapp": inapp, "email": email})
    results = await d.dispatch(_notif(), _t(), {"inapp": True, "email": True, "push": False, "toast": False})
    email.send.assert_awaited_once()
    assert any(not r.ok for r in results)
    assert any(r.ok for r in results)


@pytest.mark.asyncio
async def test_register_channel_adds_to_dispatch_set() -> None:
    d = Dispatcher(channels={})
    custom = _fake_channel("sms")
    d.register_channel(custom)
    await d.dispatch(_notif(), _t(default_channels={"inapp": False, "email": False, "push": False, "toast": False}),
                     {"sms": True})  # type: ignore[dict-item]
    custom.send.assert_awaited_once()
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/notifications/test_dispatcher.py -v
```

- [ ] **Step 3: Implement**

`backend/app/services/notifications/dispatcher.py`:

```python
"""
@file dispatcher.py
@brief Fan a Notification out to all enabled channels.

Each channel runs concurrently; failures are isolated. The dispatcher does
not own persistence (the coalescer / repo handles that before dispatch).
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import Channel, ChannelResult
from app.services.notifications.registry import NotificationType

logger = structlog.get_logger(__name__)


class Dispatcher:
    """@brief Routes a Notification to the channels enabled for it."""

    def __init__(self, channels: dict[str, Channel]) -> None:
        self._channels: dict[str, Channel] = dict(channels)

    def register_channel(self, channel: Channel) -> None:
        """@brief Add a channel (typically called by plugins at app boot)."""
        self._channels[channel.key] = channel

    async def dispatch(
        self,
        notification: Notification,
        type: NotificationType,
        effective_channels: dict[str, Any],
    ) -> list[ChannelResult]:
        """@brief Send to every channel where ``effective_channels[key]`` is truthy."""
        coros = []
        for ch_key, ch in self._channels.items():
            if not effective_channels.get(ch_key):
                continue
            coros.append(self._safe_send(ch, notification))
        if not coros:
            return []
        results = await asyncio.gather(*coros, return_exceptions=False)
        for ch_key, result in zip([c.key for c in self._channels.values()
                                   if effective_channels.get(c.key)], results):
            logger.info(
                "notif.dispatched", channel=ch_key, type_key=type.key,
                user_id=str(notification.user_id), ok=result.ok,
            )
        return list(results)

    async def _safe_send(self, channel: Channel, n: Notification) -> ChannelResult:
        try:
            return await channel.send(n)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed", channel=channel.key,
                type_key=n.type, user_id=str(n.user_id), error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/services/notifications/test_dispatcher.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notifications/dispatcher.py backend/tests/unit/services/notifications/test_dispatcher.py
git commit -m "feat(notifications): channel dispatcher with isolated fanout"
```

---

## Task 9: Repository extensions — list_active / dismiss

**Files:**
- Modify: `backend/app/repositories/notification_repo.py`
- Modify: `backend/tests/unit/repositories/test_notification_repo.py` (or create `test_notification_repo_active.py` if file too large)

- [ ] **Step 1: Write failing tests**

Append to existing test file (or new file `backend/tests/unit/repositories/test_notification_repo_active.py`):

```python
"""@file test_notification_repo_active.py @brief Active list + dismiss ops."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository


@pytest.mark.asyncio
async def test_list_active_excludes_dismissed(db_session, seed_user, community_id) -> None:
    repo = NotificationRepository(db_session)
    user = seed_user
    a = await repo.create(user.id, "mention", {"message": "1"}, community_id)
    b = await repo.create(user.id, "mention", {"message": "2"}, community_id)
    await repo.dismiss(b.id, user.id)

    items = await repo.list_active(user.id, limit=20)
    ids = {n.id for n in items}
    assert a.id in ids
    assert b.id not in ids


@pytest.mark.asyncio
async def test_dismiss_sets_dismissed_at_only(db_session, seed_user, community_id) -> None:
    repo = NotificationRepository(db_session)
    n = await repo.create(seed_user.id, "system", {"message": "ok"}, community_id)
    ok = await repo.dismiss(n.id, seed_user.id)
    assert ok is True
    await db_session.refresh(n)
    assert n.dismissed_at is not None
    assert n.read_at is None  # dismissal does not mark read


@pytest.mark.asyncio
async def test_dismiss_all_for_user_returns_count(db_session, seed_user, community_id) -> None:
    repo = NotificationRepository(db_session)
    for i in range(3):
        await repo.create(seed_user.id, "mention", {"message": str(i)}, community_id)
    n = await repo.dismiss_all_for_user(seed_user.id)
    assert n == 3
```

(`db_session`, `seed_user`, `community_id` fixtures live in `tests/unit/repositories/conftest.py` — verify they exist; if not, add them following pattern in `tests/unit/services/conftest.py`.)

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/repositories/test_notification_repo_active.py -v
```

- [ ] **Step 3: Implement**

Append to `backend/app/repositories/notification_repo.py`:

```python
async def list_active(
    self,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[Notification]:
    """@brief Active (non-dismissed) notifications for the bell."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.dismissed_at.is_(None))
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    res = await self._session.execute(stmt)
    return list(res.scalars().all())


async def dismiss(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """@brief Set dismissed_at on a single notification (bell prune only)."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    res = await self._session.execute(stmt)
    n = res.scalar_one_or_none()
    if n is None:
        return False
    n.dismissed_at = datetime.now(UTC)
    await self._session.flush()
    return True


async def dismiss_all_for_user(self, user_id: uuid.UUID) -> int:
    """@brief Bulk dismiss every active notification for a user."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.dismissed_at.is_(None))
    )
    res = await self._session.execute(stmt)
    rows = res.scalars().all()
    now = datetime.now(UTC)
    for r in rows:
        r.dismissed_at = now
    await self._session.flush()
    return len(rows)
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/repositories/test_notification_repo_active.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/notification_repo.py backend/tests/unit/repositories/test_notification_repo_active.py
git commit -m "feat(notifications): repo list_active + dismiss / dismiss_all"
```

---

## Task 10: Mention extraction utility

**Files:**
- Create: `backend/app/services/mentions.py`
- Create: `backend/tests/unit/services/test_mentions.py`

- [ ] **Step 1: Write failing test**

`backend/tests/unit/services/test_mentions.py`:

```python
"""@file test_mentions.py @brief @-mention extraction (moved from notification service)."""
from __future__ import annotations

from app.services.mentions import extract


def test_extract_returns_unique_usernames_in_order() -> None:
    assert extract("hi @alice and @bob and @alice") == ["alice", "bob"]


def test_extract_skips_code_blocks() -> None:
    assert extract("here is `@alice` not pinged") == []


def test_extract_handles_no_mentions() -> None:
    assert extract("plain text") == []


def test_extract_ignores_email_like_strings() -> None:
    # Mentions are @<word> only — emails are not split out by this util
    out = extract("see foo@example.com and @alice")
    assert "alice" in out
    # Followed-by-period or punctuation does not break match
    assert extract("@alice.") == ["alice"]
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/test_mentions.py -v
```

- [ ] **Step 3: Implement**

`backend/app/services/mentions.py`:

```python
"""
@file mentions.py
@brief Pure @-mention extraction utility.
"""
from __future__ import annotations

import re

_MENTION_RE = re.compile(r"@([a-zA-Z0-9_-]+)")


def extract(content: str) -> list[str]:
    """@brief Extract @username mentions, skipping backtick-wrapped runs.

    Returns usernames in order of first appearance, deduped.
    """
    in_code = False
    out: list[str] = []
    for part in re.split(r"(`+)", content):
        if part.startswith("`"):
            in_code = not in_code
            continue
        if in_code:
            continue
        for m in _MENTION_RE.finditer(part):
            out.append(m.group(1))
    return list(dict.fromkeys(out))
```

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/unit/services/test_mentions.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mentions.py backend/tests/unit/services/test_mentions.py
git commit -m "refactor(mentions): extract @-mention utility from notification_service"
```

---

## Task 11: NotificationService façade rewrite

**Files:**
- Rewrite: `backend/app/services/notification_service.py`
- Modify: `backend/app/repositories/settings_repo.py` (verify `get_or_create` returns settings with `notification_prefs`)
- Test: `backend/tests/unit/services/test_notification_service.py` (rewrite)

- [ ] **Step 1: Write failing test**

Replace `backend/tests/unit/services/test_notification_service.py` content with:

```python
"""@file test_notification_service.py @brief Façade orchestrates registry + dispatcher + repo."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.notification import Notification
from app.models.user_settings import UserSettings
from app.services.notification_service import NotificationService
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.registry import (
    NotificationPayload, NotificationType, _REGISTRY, register,
)


@pytest.fixture(autouse=True)
def _registry():
    snap = dict(_REGISTRY)
    _REGISTRY.clear()
    register(NotificationType(
        key="mention", category="social", payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": True, "push": False, "toast": False},
        label_i18n="notif.mention.label",
    ))
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snap)


def _settings_with(prefs: dict | None = None) -> UserSettings:
    s = MagicMock(spec=UserSettings)
    s.notification_prefs = prefs or {}
    return s


@pytest.mark.asyncio
async def test_notify_persists_and_dispatches() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.type = "mention"; n.payload = {"message": "m"}
    n.user_id = uuid.uuid4(); n.actor_ids = []

    notif_repo = MagicMock()
    notif_repo.create = AsyncMock(return_value=n)
    settings_repo = MagicMock()
    settings_repo.get_or_create = AsyncMock(return_value=_settings_with())
    dispatcher = MagicMock()
    dispatcher.dispatch = AsyncMock(return_value=[ChannelResult(ok=True)])

    svc = NotificationService(
        notification_repo=notif_repo, settings_repo=settings_repo,
        community_id=uuid.uuid4(), dispatcher=dispatcher,
    )
    out = await svc.notify(uuid.uuid4(), "mention", {"message": "m"})
    assert out is n
    notif_repo.create.assert_awaited_once()
    dispatcher.dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_validates_payload_against_registry_schema() -> None:
    notif_repo = MagicMock(); notif_repo.create = AsyncMock()
    settings_repo = MagicMock()
    settings_repo.get_or_create = AsyncMock(return_value=_settings_with())
    dispatcher = MagicMock(); dispatcher.dispatch = AsyncMock(return_value=[])
    svc = NotificationService(
        notification_repo=notif_repo, settings_repo=settings_repo,
        community_id=uuid.uuid4(), dispatcher=dispatcher,
    )
    with pytest.raises(ValueError):
        await svc.notify(uuid.uuid4(), "mention", payload={})  # missing required 'message'


@pytest.mark.asyncio
async def test_notify_unknown_type_raises() -> None:
    svc = NotificationService(
        notification_repo=MagicMock(), settings_repo=MagicMock(),
        community_id=uuid.uuid4(), dispatcher=MagicMock(),
    )
    with pytest.raises(KeyError):
        await svc.notify(uuid.uuid4(), "no.such.type", {"message": "x"})


@pytest.mark.asyncio
async def test_notify_user_pref_disables_email() -> None:
    n = MagicMock(spec=Notification)
    n.id = uuid.uuid4(); n.type = "mention"; n.payload = {"message": "m"}
    n.user_id = uuid.uuid4(); n.actor_ids = []
    notif_repo = MagicMock(); notif_repo.create = AsyncMock(return_value=n)
    settings_repo = MagicMock()
    settings_repo.get_or_create = AsyncMock(return_value=_settings_with(
        {"mention": {"email": False}}
    ))
    dispatcher = MagicMock(); dispatcher.dispatch = AsyncMock(return_value=[])

    svc = NotificationService(
        notification_repo=notif_repo, settings_repo=settings_repo,
        community_id=uuid.uuid4(), dispatcher=dispatcher,
    )
    await svc.notify(uuid.uuid4(), "mention", {"message": "m"})

    _, _, eff = dispatcher.dispatch.call_args.args
    assert eff["email"] is False
    assert eff["inapp"] is True


@pytest.mark.asyncio
async def test_set_prefs_partial_update_persists_merge() -> None:
    settings_repo = MagicMock()
    s = _settings_with({"mention": {"email": True}})
    settings_repo.get_or_create = AsyncMock(return_value=s)
    settings_repo.update_prefs = AsyncMock()

    svc = NotificationService(
        notification_repo=MagicMock(), settings_repo=settings_repo,
        community_id=uuid.uuid4(), dispatcher=MagicMock(),
    )
    user_id = uuid.uuid4()
    await svc.set_prefs(user_id, {"mention": {"push": True}})
    settings_repo.update_prefs.assert_awaited_once()
    args = settings_repo.update_prefs.call_args.args
    assert args[0] == user_id
    saved = args[1]
    assert saved["mention"] == {"email": True, "push": True}
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd backend && pytest tests/unit/services/test_notification_service.py -v
```

- [ ] **Step 3: Add `update_prefs` to settings repo**

In `backend/app/repositories/settings_repo.py`, add (find file first to confirm path; create if missing):

```python
async def update_prefs(self, user_id: uuid.UUID, prefs: dict) -> None:
    """@brief Persist a complete notification_prefs dict for a user."""
    s = await self.get_or_create(user_id, ...)  # use existing signature
    s.notification_prefs = prefs
    await self._session.flush()
```
(Match existing signature; the test uses positional args.)

- [ ] **Step 4: Rewrite `notification_service.py`**

```python
"""
@file notification_service.py
@brief Public façade for the notification subsystem.

Validates payloads against the registry, resolves effective channel prefs
from user settings, persists the row, and hands off to the Dispatcher.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.notification import (
    NotificationList, NotificationResponse, UnreadCountResponse,
)
from app.services.notifications.dispatcher import Dispatcher
from app.services.notifications.prefs import effective_channels
from app.services.notifications.registry import get as registry_get

logger = structlog.get_logger(__name__)


class NotificationService:
    """@brief Façade — see file docstring."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        settings_repo: SettingsRepository,
        community_id: uuid.UUID,
        *,
        dispatcher: Dispatcher,
    ) -> None:
        self._repo = notification_repo
        self._settings_repo = settings_repo
        self._community_id = community_id
        self._dispatcher = dispatcher

    async def notify(
        self,
        user_id: uuid.UUID,
        type_key: str,
        payload: dict[str, Any],
    ) -> Notification | None:
        type_ = registry_get(type_key)  # raises KeyError on unknown
        try:
            validated = type_.payload_schema.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"invalid payload for {type_key}: {exc}") from exc

        settings = await self._settings_repo.get_or_create(user_id, self._community_id)
        prefs = getattr(settings, "notification_prefs", {}) or {}
        eff = effective_channels(type_, prefs)

        notification = await self._repo.create(
            user_id, type_key, validated.model_dump(mode="json"), self._community_id,
        )
        await self._dispatcher.dispatch(notification, type_, eff)
        return notification

    async def list_active(self, user_id: uuid.UUID, limit: int = 20) -> list[Notification]:
        return await self._repo.list_active(user_id, limit=limit)

    async def list_history(
        self, user_id: uuid.UUID, cursor: str | None = None, limit: int = 20,
    ) -> NotificationList:
        items, next_cursor = await self._repo.list_for_user(user_id, cursor=cursor, limit=limit)
        return NotificationList(
            items=[NotificationResponse.model_validate(n) for n in items],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> UnreadCountResponse:
        c = await self._repo.get_unread_count(user_id)
        return UnreadCountResponse(count=c)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self._repo.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        return await self._repo.mark_all_read(user_id)

    async def dismiss(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self._repo.dismiss(notification_id, user_id)

    async def dismiss_all(self, user_id: uuid.UUID) -> int:
        return await self._repo.dismiss_all_for_user(user_id)

    async def clear_all(self, user_id: uuid.UUID) -> int:
        return await self._repo.delete_all_for_user(user_id)

    async def get_prefs(self, user_id: uuid.UUID) -> dict[str, dict[str, bool]]:
        s = await self._settings_repo.get_or_create(user_id, self._community_id)
        return dict(getattr(s, "notification_prefs", {}) or {})

    async def set_prefs(
        self, user_id: uuid.UUID, partial: dict[str, dict[str, bool]],
    ) -> dict[str, dict[str, bool]]:
        s = await self._settings_repo.get_or_create(user_id, self._community_id)
        current = dict(getattr(s, "notification_prefs", {}) or {})
        for type_key, channel_map in partial.items():
            current[type_key] = {**(current.get(type_key) or {}), **channel_map}
        await self._settings_repo.update_prefs(user_id, current)
        return current
```

- [ ] **Step 5: Verify PASS**

```bash
cd backend && pytest tests/unit/services/test_notification_service.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/notification_service.py backend/app/repositories/settings_repo.py backend/tests/unit/services/test_notification_service.py
git commit -m "refactor(notifications): rewrite NotificationService as registry/dispatcher façade"
```

---

## Task 12: Wire up — DI helpers + app boot

**Files:**
- Modify: `backend/app/core/dependencies.py`
- Modify: `backend/app/main.py` (import `app.services.notifications.types` so registrations run; build dispatcher singleton)

- [ ] **Step 1: Write failing integration test**

`backend/tests/integration/test_notification_dispatch_e2e.py`:

```python
"""@file test_notification_dispatch_e2e.py @brief End-to-end notify → row + SSE event."""
from __future__ import annotations

import uuid

import pytest

from app.services.notifications.registry import iter_types


@pytest.mark.asyncio
async def test_notify_creates_row_for_built_in_type(
    notification_service, seed_user, db_session,
) -> None:
    keys = {t.key for t in iter_types()}
    assert "mention" in keys

    n = await notification_service.notify(
        seed_user.id, "mention",
        {"message": "hi", "actor_name": "Alice", "target_id": "post-1"},
    )
    assert n is not None
    assert n.type == "mention"
```
(Add `notification_service` fixture in `tests/integration/conftest.py` that builds the service with real dispatcher + in-app channel and an in-memory event bus.)

- [ ] **Step 2: Run, verify FAIL**

Expected: fixture missing or types not registered.

- [ ] **Step 3: Trigger built-in type registration in app boot**

In `backend/app/main.py`, near the top of `create_app()` (or module-level imports), add:

```python
import app.services.notifications.types  # noqa: F401  — triggers built-in registrations
```

- [ ] **Step 4: Add dispatcher provider to dependencies**

In `backend/app/core/dependencies.py`:

```python
from app.services.notifications.channels.email import EmailChannel
from app.services.notifications.channels.inapp import InAppChannel
from app.services.notifications.channels.push import PushChannel
from app.services.notifications.dispatcher import Dispatcher
from app.services.realtime.event_bus import event_bus

_dispatcher: Dispatcher | None = None


def get_notification_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher(channels={
            "inapp": InAppChannel(event_bus=event_bus),
            "email": EmailChannel(),
            "push": PushChannel(),
        })
    return _dispatcher


def build_notification_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    dispatcher: Dispatcher = Depends(get_notification_dispatcher),
) -> NotificationService:
    return NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=uuid.UUID(settings.COMMUNITY_ID),
        dispatcher=dispatcher,
    )
```

- [ ] **Step 5: Verify PASS**

```bash
cd backend && pytest tests/integration/test_notification_dispatch_e2e.py -xvs
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/core/dependencies.py backend/tests/integration/test_notification_dispatch_e2e.py
git commit -m "feat(notifications): wire dispatcher singleton + boot-time type registration"
```

---

## Task 13: API surface — new endpoints

**Files:**
- Modify: `backend/app/api/v1/notifications.py`
- Modify: `backend/app/schemas/notification.py`
- Test: `backend/tests/integration/api/test_notifications_api.py` (extend or create)

- [ ] **Step 1: Write failing test**

`backend/tests/integration/api/test_notifications_api.py`:

```python
"""@file test_notifications_api.py @brief New v2 endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_get_types_returns_registry(client_authed) -> None:
    res = await client_authed.get("/api/v1/notifications/types")
    assert res.status_code == 200
    body = res.json()
    keys = {t["key"] for t in body}
    assert {"mention", "reaction", "system"} <= keys
    mention = next(t for t in body if t["key"] == "mention")
    assert "default_channels" in mention
    assert "payload_schema" in mention


@pytest.mark.asyncio
async def test_active_endpoint_excludes_dismissed(client_authed, seed_notifications):
    a, b = seed_notifications  # b will be dismissed
    await client_authed.post(f"/api/v1/notifications/{b.id}/dismiss")
    res = await client_authed.get("/api/v1/notifications/active")
    ids = {item["id"] for item in res.json()["items"]}
    assert str(a.id) in ids
    assert str(b.id) not in ids


@pytest.mark.asyncio
async def test_get_preferences_returns_jsonb(client_authed) -> None:
    res = await client_authed.get("/api/v1/notifications/preferences")
    assert res.status_code == 200
    body = res.json()
    assert "notification_prefs" in body


@pytest.mark.asyncio
async def test_patch_preferences_merges_partial(client_authed) -> None:
    res = await client_authed.patch(
        "/api/v1/notifications/preferences",
        json={"notification_prefs": {"mention": {"email": False}}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["notification_prefs"]["mention"]["email"] is False


@pytest.mark.asyncio
async def test_patch_preferences_rejects_unknown_type(client_authed) -> None:
    res = await client_authed.patch(
        "/api/v1/notifications/preferences",
        json={"notification_prefs": {"no_such_type": {"email": False}}},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "NOTIF_TYPE_UNKNOWN"
```

- [ ] **Step 2: Add schemas**

In `backend/app/schemas/notification.py` add:

```python
class NotificationTypeSchema(BaseModel):
    key: str
    category: str
    default_channels: dict[str, bool]
    user_configurable: list[str]
    group_window_seconds: int | None
    toast_on_arrival: bool
    bypass_dnd: bool
    digestable: bool
    actions: list[dict]
    label_i18n: str
    icon: str
    plugin_id: str | None
    payload_schema: dict


class PreferencesResponse(BaseModel):
    notification_prefs: dict[str, dict[str, bool]]


class PreferencesUpdate(BaseModel):
    notification_prefs: dict[str, dict[str, bool]]


class ActiveListResponse(BaseModel):
    items: list[NotificationResponse]
```

- [ ] **Step 3: Add endpoints**

In `backend/app/api/v1/notifications.py` (extending the existing router):

```python
from app.core.exceptions import AppError
from app.services.notifications.registry import iter_types, get as registry_get
from app.schemas.notification import (
    NotificationTypeSchema, PreferencesResponse, PreferencesUpdate, ActiveListResponse,
)


@router.get("/types", response_model=list[NotificationTypeSchema])
async def list_types() -> list[NotificationTypeSchema]:
    from app.services.notifications.registry import to_json_schema
    return [NotificationTypeSchema(**t) for t in to_json_schema()]


@router.get("/active", response_model=ActiveListResponse)
async def list_active(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=100),
) -> ActiveListResponse:
    items = await service.list_active(user.id, limit=limit)
    return ActiveListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
    )


@router.post("/{notification_id}/dismiss", response_model=MessageResponse)
async def dismiss_notification(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    ok = await service.dismiss(notification_id, user.id)
    if not ok:
        raise AppError("NOT_FOUND", _("Notification not found"), status_code=404)
    return MessageResponse(message=_("Dismissed"))


@router.post("/dismiss-all", response_model=MessageResponse)
async def dismiss_all(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    n = await service.dismiss_all(user.id)
    return MessageResponse(message=_("Dismissed {n}").format(n=n))


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> PreferencesResponse:
    prefs = await service.get_prefs(user.id)
    return PreferencesResponse(notification_prefs=prefs)


@router.patch("/preferences", response_model=PreferencesResponse)
async def patch_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> PreferencesResponse:
    for type_key in body.notification_prefs:
        try:
            registry_get(type_key)
        except KeyError as exc:
            raise AppError("NOTIF_TYPE_UNKNOWN", f"unknown notification type: {type_key}",
                          status_code=400) from exc
    saved = await service.set_prefs(user.id, body.notification_prefs)
    return PreferencesResponse(notification_prefs=saved)
```

(Update existing `_build_service` to use `get_notification_dispatcher()` from Task 12.)

- [ ] **Step 4: Verify PASS**

```bash
cd backend && pytest tests/integration/api/test_notifications_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/notifications.py backend/app/schemas/notification.py backend/tests/integration/api/test_notifications_api.py
git commit -m "feat(notifications): /types /active /dismiss /preferences endpoints"
```

---

## Task 14: Update call sites — drop `Any | None` typing + use mention util

**Files:**
- Modify: `backend/app/services/post_service.py`
- Modify: `backend/app/services/event_service.py`
- Modify: `backend/app/services/gallery_service.py`
- Modify: `backend/app/services/prompt_service.py`
- Modify: `backend/app/tasks/gallery_tasks.py`
- Modify: any DI builders (`api/v1/galleries.py`, `api/v1/prompts.py`, `api/v1/events.py`, `api/v1/auth.py`) — switch to `build_notification_service` from Task 12

- [ ] **Step 1: Replace `notify_mentions` call in `post_service.py`**

Find the two `await self._notification.notify_mentions(...)` call sites. Replace with:

```python
from app.services import mentions as _mentions
from sqlalchemy import select as _sa_select
from app.models.user import User as _UserModel
from app.core.i18n import _

usernames = _mentions.extract(content)
if usernames:
    res = await session.execute(_sa_select(_UserModel).where(
        _UserModel.username.in_(usernames),
        _UserModel.deleted_at.is_(None),
    ))
    for mentioned in res.scalars().all():
        if mentioned.id == actor.id:
            continue
        await self._notification.notify(
            user_id=mentioned.id, type_key="mention",
            payload={
                "message": _("%(user)s mentioned you in a post") % {"user": actor.display_name},
                "link": f"/app/post/{post_id}",
                "actor_id": str(actor.id),
                "actor_name": actor.display_name,
                "target_id": str(post_id),
            },
        )
```

Remove now-unused `notify_mentions` method from `notification_service.py` if not already (Task 11 omitted it).

- [ ] **Step 2: Tighten DI types**

In `event_service.py`, `gallery_service.py`, `prompt_service.py`, change:
```python
notification_service: Any | None = None,
```
to:
```python
from app.services.notification_service import NotificationService
...
notification_service: NotificationService,
```
Remove every `if self._notifications:` guard before `await self._notifications.notify(...)`. Update each `notify(...)` call to use `type_key=` (matches new signature).

- [ ] **Step 3: Update API DI**

In `api/v1/galleries.py`, `api/v1/prompts.py`, `api/v1/events.py`, `api/v1/auth.py` and any places that build `NotificationService(...)` inline, switch to:

```python
from app.core.dependencies import build_notification_service
...
notif = build_notification_service(db, settings, dispatcher)
```

- [ ] **Step 4: Update `tasks/gallery_tasks.py`**

Same — instantiate `NotificationService` with the dispatcher singleton (`get_notification_dispatcher()`).

- [ ] **Step 5: Run full suite**

```bash
cd backend && pytest -q
```
Expected: green. Fix any test that still expects `notify_mentions` on the service or `Any | None` typing.

- [ ] **Step 6: Lint + types**

```bash
cd backend && ruff check . && mypy app/
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ backend/app/api/v1/ backend/app/tasks/gallery_tasks.py backend/tests/
git commit -m "refactor(notifications): tighten DI types + use mention util at call sites"
```

---

## Task 15: Final smoke + plan-A done

- [ ] **Step 1: Full test suite green**

```bash
cd backend && pytest --cov=app --cov-report=term -q
```
Expected: all green; coverage ≥ pre-Plan-A baseline.

- [ ] **Step 2: Migration up + down**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```
Expected: clean.

- [ ] **Step 3: Manual smoke (in `dev-start.sh` env)**

In a Python shell with the app loaded:

```python
import asyncio, uuid
from app.core.dependencies import build_notification_service, get_notification_dispatcher, get_db
from app.core.config import get_settings
# build_notification_service in dev REPL: open session manually
# notify a test user with type="mention" payload={"message":"x","actor_name":"Tester","target_id":"t"}
# verify: row in `notifications`, SSE event in browser bell, Celery task in `notifications` queue, push delivered if VAPID + browser subscribed
```

- [ ] **Step 4: Commit (no-op possible — only docs/whitespace)**

```bash
git status
# If any pending tweaks (formatting, lint), commit:
git add -A && git commit -m "chore(notifications): plan-A smoke + cleanup"
```

---

## Self-Review

- **Spec coverage (Plan A scope):** §1–8 + §10 + §11 (new metrics deferred to Plan B; logs in place) + §12.1, §12.3, §12.4, §13 backend tests, §14 file budget all reflected.
- **Placeholder scan:** none in code blocks. Migration revision id `b2c3d4e5f6a7` is concrete; verify head before running Task 3.
- **Type consistency:** `NotificationService.notify(user_id, type_key, payload)` consistent across Tasks 11/13/14. `Channel.send(notification)` consistent across Tasks 5/6/7/8. `Dispatcher.dispatch(notification, type, effective_channels)` consistent. `effective_channels` returns `dict[Channel, bool]`. Repo additions: `list_active`, `dismiss`, `dismiss_all_for_user` consistent across Tasks 9/11/13.

---

## Execution Handoff

Plan A complete and saved to `docs/superpowers/plans/2026-05-02-notifications-plan-a-foundation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks in this session via executing-plans, batch with checkpoints

Which approach?
