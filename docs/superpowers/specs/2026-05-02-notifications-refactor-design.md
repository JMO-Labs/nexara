# Notifications Refactor — Design Spec

- **Date:** 2026-05-02
- **Branch (origin):** `polish/phase-5-motion`
- **Status:** Draft → pending user review
- **Scope class:** Full overhaul (registry-driven, plugin-extensible, multi-channel, grouped, DnD, digest, webhooks, drawer + bell)

---

## 1. Problem

Current notification system is inconsistent, partially wired, and hard to extend:

- **Push channel orphaned.** `PUSH_PREF_MAP` and `PushService.should_send_push` exist, but `NotificationService.notify()` never invokes push. Celery `send_push_notification` task is a stub that only logs.
- **Type registry duplicated 5×.** `NOTIFICATION_TYPES` tuple, `PREF_MAP`, `PUSH_PREF_MAP`, frontend `TYPE_META`, settings `notifTypes` array. Adding a new type requires touching ~5 files plus an Alembic migration to add `user_settings` columns.
- **Untyped payload.** `payload: dict[str, Any]` everywhere. Frontend reads `payload.message` / `payload.link` ad hoc; no schema, no validation, no per-type renderer.
- **No grouping / coalescing.** 100 reactions in 10 minutes = 100 rows + 100 pushes + 100 emails.
- **Disconnected surfaces.** `NotificationsBell` (server SSE) and `ToastRoot` (client zustand) do not talk to each other. SSE-delivered notifications never auto-toast; user must open the bell.
- **Settings UI hardcodes 6 of 12 types** and exposes no Push column despite push prefs existing in the model.
- **Inconsistent DI.** `auth_service` is typed `NotificationService`; gallery/event/prompt services type it `Any | None` and silently no-op when missing.
- **No plugin extensibility.** Future plugins cannot register new notification types without forking core code and writing a migration.
- **No DnD, no digests, no webhooks, no inline actions, no notification-history page.**

## 2. Goals

1. Single source of truth for notification types: an in-process registry.
2. Adding a notification type (core or plugin) is a single `register(...)` call — no migration, no UI edits, no settings columns.
3. All channels (`inapp`, `email`, `push`, `toast`, `webhook`) wired through one dispatcher with consistent prefs, DnD, and grouping behavior.
4. Bell shows only active/relevant notifications; click-to-navigate or ack auto-prunes from the bell. Drawer holds the full history with filters and bulk actions.
5. Plugin authors get a documented extension surface: register a `NotificationType`, optionally register a custom channel.
6. Match repo testing bar (~85% coverage, TDD).

## 3. Non-goals (v1)

- SMS / Telegram / Matrix channels (extension hook will exist; no built-in implementation).
- Notification analytics dashboard (metrics emitted, dashboards out of scope).
- Cross-community notification routing.
- Mobile-native push beyond Web Push (PWA already covers this).

## 4. Architecture Overview

```
                ┌─────────────────────────────────────┐
                │  NotificationRegistry (in-process)  │
                │  type_key → NotificationType        │
                └─────────────────┬───────────────────┘
                                  │ discovers
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌──────────────┐        ┌──────────────────┐        ┌──────────────┐
│ Dispatcher   │ ◄──────│ NotificationSvc  │───────►│ Settings UI  │
│ (channels)   │        │ .notify()        │        │ (auto-built) │
└──────┬───────┘        └────────┬─────────┘        └──────────────┘
       │                         │ persist (UPSERT-by-group_key)
   ┌───┼────┬────────┬─────────┐ ▼
   ▼   ▼    ▼        ▼         ▼ Notifications
 inapp email push  webhook   group_coalescer
 (SSE) (digest) (web push) (HMAC POST + retry)
                  ▲
                  └── digest_dispatch (Celery beat, every 5 min)
```

### 4.1 Backend layout

| Path | Purpose |
|---|---|
| `services/notifications/registry.py` | `NotificationType`, `Action`, `Channel`, `register()`, `get()`, `iter_types()`, `to_json_schema()` |
| `services/notifications/types/__init__.py` | Imports every built-in type module so registration runs on app boot |
| `services/notifications/types/<key>.py` | One module per built-in type; defines payload schema and calls `register(...)` |
| `services/notifications/dispatcher.py` | Channel fanout, DnD gate, parallel send |
| `services/notifications/coalescer.py` | Group-key windowed UPSERT |
| `services/notifications/dnd.py` | Schedule + manual snooze evaluation (tz/DST-aware) |
| `services/notifications/digest.py` | Drain queue + render digest emails |
| `services/notifications/channels/{inapp,email,push,webhook}.py` | Uniform `Channel` interface |
| `services/notification_service.py` | Public façade: `notify`, `list_active`, `list_history`, `mark_read`, `dismiss`, `bulk_*`, `set_dnd`, `snooze`, `set_prefs` |
| `services/mentions.py` | Pure mention-extraction utility (moved off `NotificationService`) |
| `repositories/notification_repo.py` | Extended: `upsert_grouped`, `list_active`, `list_history`, `dismiss`, digest queue ops |
| `repositories/webhook_repo.py` | New: per-user + per-community webhook subs |
| `tasks/notification_tasks.py` | `send_email_notification` (existing), `send_push_notification` (replace stub), `digest_dispatch` (beat), `send_digest_email`, `webhook_deliver` |

### 4.2 Frontend layout

| Path | Purpose |
|---|---|
| `lib/notifications/registry.ts` | Mirror of backend registry; hydrated once via `GET /notifications/types` (react-query, `staleTime: Infinity`) |
| `lib/notifications/renderers.ts` | `renderNotif(type, payload, t)` → `{title, body, icon, link, actions[]}` |
| `components/notifications/NotificationsBell.tsx` | Compact, active/unread only; click-or-ack prunes |
| `components/notifications/NotificationsDrawer.tsx` | Right slide-out; full history, filters, bulk actions, restore |
| `components/notifications/NotifRow.tsx` | Registry-driven row renderer (icon + actions) |
| `components/notifications/ToastBridge.tsx` | SSE `user_toast` / `user_notification` (filtered by `type.toast_on_arrival`) → toast |
| `components/settings/NotificationsTab.tsx` | Auto-built matrix; DnD editor; webhook list |
| `components/settings/DnDScheduleEditor.tsx` | Weekly grid + tz picker |
| `components/settings/WebhookList.tsx` + `WebhookEditModal.tsx` | CRUD; secret revealed once on create |
| `stores/notifications.ts` | `dismissOptimistic`, `bulkSelection`, `drawerOpen` |
| `stores/toasts.ts` | Extended: `action?`, `priority`, `dedupeKey?` |

## 5. Type Contract

```python
# services/notifications/registry.py

Channel = Literal["inapp", "email", "push", "webhook", "toast"]

class NotificationPayload(BaseModel):
    message: str                # short, server-side i18n-rendered
    link: str | None = None
    actor_id: str | None = None
    target_id: str | None = None  # post/event/etc — used as group key seed

@dataclass(frozen=True)
class Action:
    key: str
    label_i18n: str
    method: Literal["POST", "PUT", "DELETE"]
    url_template: str            # tokens: {target_id}, {actor_id}
    style: Literal["primary", "neutral", "danger"] = "neutral"

@dataclass(frozen=True)
class NotificationType:
    key: str
    category: Literal["social", "event", "gallery", "prompt", "system", "plugin"]
    payload_schema: type[NotificationPayload]
    default_channels: dict[Channel, bool]
    user_configurable: tuple[Channel, ...] = ("inapp", "email", "push", "toast")
    group_window_seconds: int | None = None    # None = no grouping
    toast_on_arrival: bool = False
    bypass_dnd: bool = False
    digestable: bool = True
    actions: tuple[Action, ...] = ()
    label_i18n: str = ""
    icon: str = "inbox"                         # heroicons name
    plugin_id: str | None = None                # set by plugin loader
```

### 5.1 Built-in type registration shape

```python
# services/notifications/types/reaction.py
class ReactionPayload(NotificationPayload):
    actor_name: str
    emoji: str
    post_excerpt: str

register(NotificationType(
    key="reaction",
    category="social",
    payload_schema=ReactionPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    digestable=True,
    label_i18n="notif.reaction.label",
    icon="heart",
))
```

### 5.2 Plugin registration shape

A plugin's package `__init__` (or a dedicated `notifications.py`) calls `register(...)`. The plugin loader sets `plugin_id` automatically. No DB writes; settings UI auto-renders the new row on next page load.

## 6. Data Model

Migration: `alembic/versions/00XX_notifications_v2.py`. Single transaction.

### 6.1 `notifications` (extend)

```sql
ALTER TABLE notifications
  ADD COLUMN group_key TEXT,
  ADD COLUMN count INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN actor_ids UUID[] NOT NULL DEFAULT '{}',
  ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN dismissed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX notifications_group_active_idx
  ON notifications(user_id, group_key)
  WHERE group_key IS NOT NULL AND read_at IS NULL;

CREATE INDEX notifications_user_active_idx
  ON notifications(user_id, dismissed_at, created_at DESC)
  WHERE dismissed_at IS NULL;
```

`read_at` and `dismissed_at` are independent:

- `read_at` — user opened/acked. Drawer history shows "read" badge.
- `dismissed_at` — bell pruned it (clicked-thru to navigation, ack button, or "mark all read").
- Bell query: `WHERE dismissed_at IS NULL`. Drawer query: all rows (filter applied client-side).

### 6.2 `user_settings` (replace per-type columns with JSONB)

```sql
ALTER TABLE user_settings
  ADD COLUMN notification_prefs JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN dnd_schedule JSONB,
  ADD COLUMN dnd_until TIMESTAMPTZ,
  ADD COLUMN dnd_timezone TEXT NOT NULL DEFAULT 'UTC',
  ADD COLUMN digest_cadence JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN digest_last_sent_at TIMESTAMPTZ;

-- Backfill: read every notif_<type>_<channel> column → write into notification_prefs.
-- Read mute_all_email / mute_all_push → set dnd_schedule = NULL (use per-type prefs instead).
-- Drop all notif_*_inapp / notif_*_email / notif_*_push columns and the two mute_all_* columns.
```

#### Pref shape

```json
{
  "reaction":   {"inapp": true, "email": false, "push": false, "toast": false},
  "mention":    {"inapp": true, "email": true,  "push": true,  "toast": true},
  "event_rsvp": {"inapp": true, "email": true,  "push": false, "toast": false}
}
```

#### DnD schedule shape

```json
{
  "mon": [{"start": "22:00", "end": "07:00"}],
  "tue": [{"start": "22:00", "end": "07:00"}],
  ...
  "sat": [],
  "sun": []
}
```
Evaluated against `dnd_timezone`. Multi-window per day supported.

#### Digest cadence shape

```json
{
  "reaction": "daily",
  "mention":  "instant",
  "comment":  "hourly",
  "new_post": "off"
}
```

### 6.3 `webhook_subscriptions` (new)

```sql
CREATE TABLE webhook_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,   -- NULL = community-level
  url TEXT NOT NULL,
  secret TEXT NOT NULL,                                  -- HMAC-SHA256 signing key
  type_keys TEXT[] NOT NULL DEFAULT '{}',                -- empty = all types
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  failure_count INTEGER NOT NULL DEFAULT 0,
  last_failure_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX webhook_subs_community_idx ON webhook_subscriptions(community_id) WHERE enabled;
CREATE INDEX webhook_subs_user_idx ON webhook_subscriptions(user_id) WHERE enabled;
```

### 6.4 `notification_digest_queue` (new)

```sql
CREATE TABLE notification_digest_queue (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type_key TEXT NOT NULL,
  notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, notification_id)
);
CREATE INDEX digest_queue_drain_idx ON notification_digest_queue(user_id, type_key, enqueued_at);
```

### 6.5 Coalescer logic

```sql
INSERT INTO notifications (user_id, type, payload, group_key, actor_ids, ...)
VALUES (...)
ON CONFLICT (user_id, group_key) WHERE group_key IS NOT NULL AND read_at IS NULL
DO UPDATE SET
  count = notifications.count + 1,
  actor_ids = (
    SELECT array_agg(DISTINCT a)
    FROM unnest(notifications.actor_ids || EXCLUDED.actor_ids) AS a
  ),
  payload = EXCLUDED.payload,        -- latest message wins
  updated_at = NOW()
WHERE NOW() - notifications.created_at < make_interval(secs => <window>);
```

If `group_window_seconds` is `NULL` for the type, fresh INSERT every time. If the conflict row's `created_at` is older than the window, the partial-index conflict still fires but the WHERE clause filters out the UPDATE — handled by retrying as fresh INSERT with `group_key = NULL` to avoid index conflict (or rotating `group_key` with a window-bucket suffix; final choice during implementation).

## 7. Dispatch Pipeline

`NotificationService.notify(user_id, type_key, payload)` runs:

1. **Validate** — `registry.get(type_key)`; `type.payload_schema.model_validate(payload)`.
2. **Resolve effective prefs** — `effective = {**type.default_channels, **user.notification_prefs.get(type_key, {})}`.
3. **DnD gate** — if `dnd_until > now` OR `in_schedule(dnd_schedule, now, tz)`:
    - if `not type.bypass_dnd`: force `email/push/toast` → `False`. In-app row still created (silent).
4. **Coalesce** — `group_key = f"{type_key}:{payload.target_id}"` if `group_window_seconds` else `None`. Repo `upsert_grouped(...)` returns either an updated existing row or a new row.
5. **Channel fanout** (parallel via `asyncio.gather(..., return_exceptions=True)`):
    - `inapp` — `event_bus.emit(user_notification(...))`
    - `toast` — `event_bus.emit(user_toast(...))` (transient; no separate row)
    - `push` — `push_service.send(...)`, suppressed if coalesced into a row whose first push was within the window
    - `email` — if `digest_cadence[type] == "instant"`: `send_email_notification.delay(...)`; else `digest_queue.enqueue(...)`
    - `webhook` — fan out to all enabled webhook subs (user-level + community-level) whose `type_keys` matches, via `webhook_deliver.delay(...)`
6. **Return** the persisted Notification.

### 7.1 Throttling

- One push per group window per `(user, group_key)`. Tracked via `notifications.created_at` of the active grouped row.
- Webhook retry: exponential backoff (Celery `autoretry_for=(httpx.HTTPError, httpx.TimeoutException)`, `max_retries=5`, `retry_backoff=True`, `retry_backoff_max=600`, `retry_jitter=True`). After `failure_count >= 10` → `enabled = false`, structured-log alert.
- Email digest: drained on `digest_dispatch` Celery beat (every 5 min). Per-type cadence determines if drain happens.

### 7.2 Channel interface (plugin extension)

```python
class Channel(Protocol):
    key: ClassVar[str]
    async def send(
        self,
        notif: Notification,
        type: NotificationType,
        user: User,
    ) -> ChannelResult: ...
```

Built-in channels register at app boot: `dispatcher.register_channel(InAppChannel())`, etc. Plugin can call `dispatcher.register_channel(MyChannel())` to add SMS/Telegram/etc.

### 7.3 Mention parsing decoupled

`notify_mentions` removed from `NotificationService`. New `services/mentions.py` module exposes `extract(content) -> list[str]`. `post_service.create_post()` calls `mentions.extract(...)`, looks up users, and loops `notification_service.notify(user_id, "mention", payload)`. Decouples parsing from delivery.

### 7.4 Digest dispatch

Beat job `digest_dispatch` (every 5 min):

```python
for user_id in users_with_pending_digests():
    settings = await settings_repo.get(user_id)
    for type_key, cadence in settings.digest_cadence.items():
        if not should_send_now(cadence, settings.digest_last_sent_at):
            continue
        rows = await digest_queue.drain(user_id, type_key)
        if not rows:
            continue
        send_digest_email.delay(user_id, type_key, [str(r.notification_id) for r in rows])
```

`should_send_now` rules:

- `instant` — never queued (handled inline in dispatcher)
- `hourly` — drain if `last_sent_at` is `NULL` or > 1h ago, AND queue non-empty
- `daily` — drain if local-time crossed user's preferred digest hour (default 08:00 in user tz) since `last_sent_at`
- `off` — never drain (rows enqueued but expire via `cleanup_old_notifications` retention)

## 8. API Surface

```
GET    /api/v1/notifications/types                    → registry JSON (cache: 1h, ETag)
GET    /api/v1/notifications                          → list (drawer); ?cursor&limit&filter[type]&filter[unread]&filter[since]
GET    /api/v1/notifications/active                   → bell list (dismissed_at IS NULL, top 20)
GET    /api/v1/notifications/unread-count             → {count, by_category: {social: 3, event: 1, ...}}
POST   /api/v1/notifications/{id}/read                → sets read_at
POST   /api/v1/notifications/{id}/dismiss             → sets dismissed_at (bell prune; history retains)
POST   /api/v1/notifications/{id}/actions/{key}       → executes registered action; validates key in type.actions
POST   /api/v1/notifications/read-all                 → ?type=&category= bulk
POST   /api/v1/notifications/dismiss-all              → bell clear
DELETE /api/v1/notifications                          → ?type=&before= bulk delete from history
DELETE /api/v1/notifications/{id}
GET    /api/v1/notifications/stream                   → SSE (existing endpoint, expanded event types)

GET    /api/v1/notifications/preferences              → {notification_prefs, dnd_*, digest_cadence}
PATCH  /api/v1/notifications/preferences              → partial update; validates against registry
POST   /api/v1/notifications/snooze                   → {duration: "1h"|"until_morning"|iso8601} → sets dnd_until
DELETE /api/v1/notifications/snooze                   → clears dnd_until

GET    /api/v1/notifications/webhooks                 → list current user's subs
POST   /api/v1/notifications/webhooks                 → create {url, type_keys[]}; returns secret once
DELETE /api/v1/notifications/webhooks/{id}
PATCH  /api/v1/notifications/webhooks/{id}            → enable/disable; edit type_keys

GET    /api/v1/communities/{id}/webhooks              → admin only; community-level
POST   /api/v1/communities/{id}/webhooks              → admin only
DELETE /api/v1/communities/{id}/webhooks/{wid}        → admin only
PATCH  /api/v1/communities/{id}/webhooks/{wid}        → admin only

POST   /api/v1/push/subscribe                         → existing
POST   /api/v1/push/unsubscribe                       → existing
GET    /api/v1/push/vapid-key                         → existing
```

### 8.1 SSE event types

Defined in `services/realtime/events.py`:

- `user_notification` — existing; payload now `{id, type, payload, group_count, actor_ids, created_at, updated_at}`
- `user_toast` — new; transient `{type, payload}` (no DB row beyond inapp if any)
- `user_notification_dismissed` — multi-tab sync; carries `{id}` so other tabs prune their bell
- `user_preferences_updated` — multi-tab sync for prefs/DnD changes

### 8.2 Webhook outbound payload

HMAC-SHA256 signed; header `X-Nexara-Signature: t=<unix_ts>,v1=<hex_sig>` (Stripe-style).

```json
{
  "id": "uuid",
  "type": "mention",
  "category": "social",
  "user_id": "uuid",
  "community_id": "uuid",
  "payload": {"message": "...", "link": "...", "..." : "..."},
  "actor_ids": ["uuid", "..."],
  "count": 3,
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```

### 8.3 Error envelope

Standard `{error: {code, message, details}}`. New codes:

- `NOTIF_TYPE_UNKNOWN` (400)
- `NOTIF_ACTION_UNKNOWN` (404)
- `NOTIF_PREF_INVALID` (400) — payload doesn't match registry shape
- `WEBHOOK_DISABLED` (409)
- `WEBHOOK_FORBIDDEN` (403) — non-admin attempting community-level write

## 9. Frontend

### 9.1 Component tree

```
TopBar
└─ NotificationsBell                        # compact, unread-only
    ├─ data:  useQuery(['notif','active'])  → /notifications/active
    ├─ count: useQuery(['notif','count'])   → /notifications/unread-count
    ├─ prune: row click (link nav) OR ack → POST /dismiss → optimistic remove
    ├─ CTA:   "View all" → opens NotificationsDrawer
    └─ NotifRow                             # registry-driven; type.icon + type.actions

NotificationsDrawer                          # right slide-out (Joy Drawer)
    ├─ Header: filters [All | Unread | by category chips], search
    ├─ Bulk toolbar: [Mark read] [Dismiss] [Delete] (when selection > 0)
    ├─ List (virtualized): NotifRow w/ checkbox, full timestamp, restore-if-dismissed
    └─ Pagination: cursor (infinite scroll)

ToastBridge                                  # mounted in app/layout
    ├─ useSSE: 'user_toast' AND 'user_notification' (filter type.toast_on_arrival)
    └─ → useToasts.push({variant, title, message, action: {label, onClick}})
                                              (click toast = navigate + dismiss notif)

SettingsTab → NotificationsTab               # rebuilt
    ├─ "Quiet hours"   (DnDScheduleEditor: weekly grid + tz)
    ├─ "Snooze now"    (1h | until morning | until tomorrow | custom)
    ├─ "Per-type matrix" (auto-built from useNotificationRegistry):
    │     Type | InApp | Email | Push | Toast | Digest cadence
    │     rows grouped by category; only renders channels in type.user_configurable
    ├─ "Push devices"  (existing PushSubscriptionRow per device)
    └─ "Webhooks"      (WebhookList + WebhookEditModal; secret shown once on create)
```

### 9.2 State

- `lib/notifications/registry.ts` — `useNotificationRegistry()` hook; react-query `staleTime: Infinity`; refetched on session start.
- `stores/notifications.ts` — new zustand: `dismissOptimistic(id)`, `bulkSelection: Set<id>`, `drawerOpen: boolean`.
- `stores/toasts.ts` — extended with `action?: {label, onClick}`, `priority: number` for sort, `dedupeKey?: string` to skip duplicate toasts within a 5s window.

### 9.3 Renderers

`lib/notifications/renderers.ts` exposes `renderNotif(type, payload, t)` returning `{title, body, icon, link, actions[]}`. Payload shapes mirrored as zod schemas keyed by `type_key`. Plugins register their own renderers via `registerRenderer(type_key, renderFn)` at module-load.

### 9.4 Multi-tab sync

SSE `user_notification_dismissed` → react-query `invalidateQueries(['notif','active','count'])`. Acking on phone makes desktop bell prune within ~1s.

### 9.5 A11y

- Bell badge: `aria-live="polite"` announces count change.
- Drawer: focus trap, Escape closes, `role="dialog"`, labelled by header.
- Toast: existing `aria-live="polite"`; `assertive` only for `danger`.
- Keyboard: `g n` opens drawer (existing keybind system); `j/k` moves selection; `e` dismisses; `Enter` activates link.

### 9.6 Empty / error states

- Bell empty: "All caught up." (Fraunces, terracotta accent — matches Warm Editorial system).
- Drawer empty (filtered): "No notifications match these filters."
- Bell load error w/ stale unread count: "Couldn't load — N unread reported. [Retry]"

## 10. Errors & Throttling Policy

- Per-channel isolation: a single channel failure never blocks others (`asyncio.gather(..., return_exceptions=True)` in dispatcher).
- All failures logged structured: `notif.channel.failed` with `channel`, `type_key`, `user_id`, `error`.
- Webhook 4xx (non-2xx, non-5xx) → no retry, increment `failure_count`.
- Webhook 5xx / timeout → retry with exponential backoff (Celery).
- Push 410 Gone → existing subscription cleanup path retained.
- Email send fail → existing Celery retry retained.
- Coalescer race (two parallel UPSERT attempts) → unique-violation caught, retry once with fresh `group_key = NULL` if window expired; otherwise re-fetch and update.
- Plugin channel raises → caught, logged, channel skipped for that dispatch only (does not disable channel globally).

## 11. Observability

New Prometheus metrics:

- `notif_dispatched_total{type, channel, result}` (result = `sent` | `suppressed_dnd` | `coalesced` | `queued_digest` | `failed`)
- `notif_dispatch_latency_seconds{channel}` (histogram)
- `webhook_delivery_failures_total{community_id_hash}`
- `webhook_disabled_total{reason}`
- `digest_emails_sent_total{type, cadence}`
- `notif_active_count{user_id_hash}` (gauge, sampled)

Structured logs (existing `structlog`): `notif.dispatched`, `notif.dnd_suppressed`, `notif.coalesced`, `notif.channel.failed`, `webhook.delivered`, `webhook.disabled`, `digest.sent`.

## 12. Migration & Rollout (clean cut)

1. **Pre-deploy code:** all 12 existing notification types registered in `services/notifications/types/` matching current behavior — UI parity day one.
2. **Migration `00XX_notifications_v2.py`** (single TX):
    - Add new columns / tables.
    - Backfill `notification_prefs` JSONB from per-type columns. Seed `digest_cadence = {<type>: "instant"}` for every type currently emailable.
    - Drop legacy `notif_*_inapp/email/push` columns + `mute_all_email/push` columns.
3. **Deploy backend + frontend together** (new schema requires new registry; new UI requires new endpoints).
4. **Smoke checklist (post-deploy):**
    - Dispatch each built-in type → assert `inapp` row exists + appropriate channels fired.
    - DnD window active → push/email/toast suppressed; in-app silent.
    - Group window active → second event coalesces, `count` increments, `actor_ids` appends.
    - Webhook delivery → HMAC verifies on test receiver.
    - Settings UI matrix renders all 12 types; edits persist; reload restores.
5. **CI gates:** ruff, mypy strict, pytest cov ≥ existing baseline, eslint, prettier, vitest cov ≥ existing.

## 13. Testing

Target: ~85% coverage, TDD throughout.

### Backend (~150 new tests)

- `tests/unit/services/notifications/test_registry.py` — register/duplicate/get/iter/json-schema export.
- `tests/unit/services/notifications/test_dispatcher.py` — channel fanout matrix, DnD gate, bypass_dnd, prefs override, parallel send isolation.
- `tests/unit/services/notifications/test_coalescer.py` — group window enter/exit, actor dedup, race (two parallel notify, same group_key).
- `tests/unit/services/notifications/test_dnd.py` — schedule eval across tz/DST; `dnd_until` expiry.
- `tests/unit/services/notifications/test_digest.py` — drain/render/cadence; `last_sent_at` advance; instant bypass; off skip.
- `tests/unit/services/notifications/test_webhook_dispatcher.py` — HMAC sig; retry; auto-disable after N failures; type_keys filter.
- `tests/unit/services/test_notification_service.py` — façade smoke; mark_read / dismiss / bulk.
- `tests/unit/repositories/test_notification_repo.py` — `upsert_grouped` happy + race; `list_active`; `dismiss`.
- `tests/unit/services/notifications/types/test_<type>.py` — one per built-in type; payload validation.
- `tests/integration/notifications/test_dispatch_e2e.py` — real Postgres + Redis; assert SSE event published.
- `tests/integration/migrations/test_notif_v2_backfill.py` — seed legacy cols, run migration, assert JSONB matches.

### Frontend (~80 new tests)

- `tests/unit/components/notifications/{Bell,Drawer,NotifRow,ToastBridge}.test.tsx` — RTL.
- `tests/unit/components/settings/NotificationsTab.test.tsx` — auto-built matrix, DnD editor, webhook CRUD.
- `tests/unit/lib/notifications/renderers.test.ts` — payload→render per type.
- `tests/unit/stores/notifications.test.ts` — optimistic dismiss/restore on error.
- E2E (Playwright): notif dispatch → bell badge → click → nav → bell prunes; multi-tab sync.

## 14. File Budget (≤400 lines/file per CLAUDE.md)

| File | Approx lines |
|---|---|
| `registry.py` | 120 |
| `dispatcher.py` | 180 |
| `coalescer.py` | 100 |
| `dnd.py` | 80 |
| `digest.py` | 120 |
| `channels/inapp.py` | 80 |
| `channels/email.py` | 120 |
| `channels/push.py` | 150 |
| `channels/webhook.py` | 180 |
| `notification_service.py` (façade) | 250 |
| `types/<key>.py` (each) | 30–60 |
| `NotificationsBell.tsx` | 200 |
| `NotificationsDrawer.tsx` | 300 |
| `NotifRow.tsx` | 150 |
| `NotificationsTab.tsx` | 350 (split if needed) |
| `DnDScheduleEditor.tsx` | 250 |
| `WebhookList.tsx` + `WebhookEditModal.tsx` | 200 + 180 |

## 15. Plugin Extension Example

```python
# my_plugin/notifications.py
from datetime import datetime
from app.services.notifications.registry import (
    register, NotificationType, NotificationPayload, Action,
)

class BookClubMeetingPayload(NotificationPayload):
    book_title: str
    meets_at: datetime

register(NotificationType(
    key="bookclub.meeting_reminder",
    category="plugin",
    payload_schema=BookClubMeetingPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    bypass_dnd=False,
    actions=(
        Action(
            key="ack",
            label_i18n="bookclub.notif.ack",
            method="POST",
            url_template="/api/v1/plugins/bookclub/meetings/{target_id}/ack",
        ),
    ),
    label_i18n="bookclub.notif.meeting_reminder",
    icon="book-open",
    plugin_id="bookclub",
))
```

That single registration gives the plugin: settings UI row (auto-rendered), all four channels wired with user-controllable prefs, group/DnD/digest/webhook fanout, inline actions in bell + drawer + toast.

## 16. Open Questions

None blocking. Decisions made during brainstorming captured in §3 of conversation log; deferred only to implementation:

- Exact group-key collision retry strategy when window expires (re-fetch vs window-bucket suffix). Either works; pick during coalescer TDD.
- Default digest hour for `daily` cadence when user hasn't set one (proposed: 08:00 user-tz).

## 17. Out-of-scope follow-ups

- Mobile-native push (FCM/APNs) — Web Push covers PWA today.
- Admin analytics dashboard for notification volume / opt-out rates.
- User-facing per-conversation mute (Slack-style mute thread).
- Scheduled notifications ("remind me in 3 days") beyond the existing Celery-driven event reminders.
