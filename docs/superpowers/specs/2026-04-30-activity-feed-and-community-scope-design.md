# Activity Feed + Community-Level Scope — Design Spec

**Date:** 2026-04-30
**Author:** Claude Code
**Status:** Draft, pending user review

## Context

The home dashboard's `ActivityWidget` currently renders the user's
`/api/v1/notifications` inbox (personal alerts only). Users want it to
behave as a community-wide "what's new" feed: posts, media uploads,
events, RSVPs, comments, chat activity, members joining, etc. — i.e.
"Sue made a new post in Family · 2h", "John added 4 photos to Trip
Album · 5h".

Adjacent gap: home aggregators (`home_service.list_media`,
`home_service.upcoming_events`) only query subgroups the viewer
belongs to. Community-root content (posts/galleries/events with
`subgroup_id IS NULL`) is never surfaced. The schema already supports
community scope on every domain (`subgroup_id` nullable on posts,
events, galleries, chat_channels) — the gap is service-layer
aggregation and create-flow exposure.

## Goals

1. Replace the activity widget's notifications source with a unified
   community-activity feed sourced from a new `activity_event` table.
2. Cover all relevant domain actions: post/event/gallery/media,
   comment/reaction/rsvp, chat (sampled), member.joined,
   subgroup.created, prompt.responded.
3. Aggregate same-actor / same-target events at read time within a
   60-minute window ("Sue added 4 photos to Trip Album").
4. Exclude the viewer's own actions from their own feed.
5. Apply visibility (community/subgroup/private) and block filtering.
6. Add community-level scope across home media, events, galleries
   aggregators (single union query, not per-subgroup loop).
7. Surface a uniform scope picker in create flows
   (post/event/gallery/channel) — `community / subgroup / private`.

Non-goals: full-text search across activity; aggregation across
distinct verbs; activity-driven push/email (those stay on the
existing `notifications` table).

## Architecture

Two coordinated changes shipped together:

**(I) `activity_event` table** — append-only log written by domain
services after their commit, read by `ActivityRepository.list_for_user`
with viewer-scoped filtering, aggregated at read time, rendered by
the activity widget.

**(II) Community-root scope** — extend the existing visibility
predicate (already used by `post_repo.list_feed` and
`event_repo.list_in_range`: "community-root rows the user can see OR
rows in user's subgroups") to media + galleries aggregators and
expose it in widget scope toggles + create-flow scope pickers.

Both share one helper: a `VisibilityScope` value object built once
per request in `home_service`:
`{community_id, viewer_id, viewer_subgroup_ids, blocked_user_ids}`.

Independent from the `notifications` table — notifications are
user-targeted alerts with read state; activity events are
community-broadcast and stateless.

## Schema

### `activity_event` table (new)

```sql
CREATE TABLE activity_event (
  id            UUID PK DEFAULT gen_random_uuid(),
  community_id  UUID NOT NULL,
  actor_id      UUID NOT NULL,
  verb          TEXT NOT NULL,                 -- 'post.created', 'media.uploaded', ...
  object_type   TEXT NOT NULL,                 -- 'post' | 'event' | 'gallery' | 'media' | 'comment' | 'rsvp' | 'reaction' | 'chat' | 'member' | 'subgroup' | 'prompt'
  object_id     UUID NOT NULL,
  target_type   TEXT NULL,                     -- 'subgroup' | 'community' | 'event' | 'post' | 'gallery'
  target_id     UUID NULL,
  subgroup_id   UUID NULL,                     -- nullable; null = community-root
  visibility    TEXT NOT NULL,                 -- 'community' | 'subgroup' | 'private'
  metadata      JSONB NOT NULL DEFAULT '{}',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX activity_event_feed_idx
  ON activity_event (community_id, created_at DESC)
  WHERE is_active;

CREATE INDEX activity_event_subgroup_idx
  ON activity_event (community_id, subgroup_id, created_at DESC)
  WHERE is_active;

CREATE INDEX activity_event_object_idx
  ON activity_event (object_type, object_id);  -- supports invalidate()
```

### `metadata` JSONB shape

Frozen at write so labels survive deletes:

```json
{
  "actor_name": "Sue",
  "object_title": "Trip Album",
  "container_title": "Family",
  "count_hint": 4
}
```

### Verb taxonomy (initial)

`post.created`, `post.commented`, `post.reacted`, `event.created`,
`event.rsvp`, `gallery.created`, `media.uploaded`, `chat.posted`
(sampled), `member.joined`, `subgroup.created`, `prompt.responded`.
New verbs added freely — no migration required.

### No FK on object_id

Heterogeneous object types make a generic FK impractical. Deletes use
`activity_repo.invalidate(object_type, object_id)` to flip
`is_active`. Read-time existence check (next section) catches misses.

## Write Path

### `ActivityRepository`

Location: `backend/app/repositories/activity_repo.py`.

```python
async def record(
    self,
    *,
    community_id: UUID,
    actor_id: UUID,
    verb: str,
    object_type: str,
    object_id: UUID,
    subgroup_id: UUID | None,
    visibility: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    metadata: dict | None = None,
) -> None: ...

async def invalidate(self, object_type: str, object_id: UUID) -> None: ...
```

`record()` wraps its insert in `try / except Exception / logger.exception`
so an activity-row write never rolls back the underlying domain
commit. The domain operation is the source of truth; the activity
log is best-effort.

### Service integration pattern

Every domain service that creates/modifies one of the listed object
types gains exactly one `await self._activity_repo.record(...)` call
after its commit. Example for `PostService.create_post`:

```python
post = await self._post_repo.create(...)
await self._session.flush()
await self._activity_repo.record(
    community_id=self._community_id,
    actor_id=user.id,
    verb="post.created",
    object_type="post",
    object_id=post.id,
    subgroup_id=post.subgroup_id,
    visibility=post.visibility,
    target_type="subgroup" if post.subgroup_id else "community",
    target_id=post.subgroup_id or self._community_id,
    metadata={
        "actor_name": user.display_name,
        "object_title": post.title or post.body[:60],
        "container_title": subgroup.name if subgroup else community.name,
    },
)
```

Delete paths call `activity_repo.invalidate(object_type, object_id)`
in the same transaction as the hard delete.

### Chat throttle

`chat.posted` is high-volume. Sample: only the **first** message in a
channel by an actor per 30-min window emits an activity row. Implemented
via a Redis SETNX:
`activity:chat:throttle:{community_id}:{actor_id}:{channel_id}` with
`TTL=1800`. `chat_service.post_message` checks the key; if SETNX
succeeds, `record()` runs.

## Read Path

### `ActivityRepository.list_for_user`

```python
async def list_for_user(
    self,
    *,
    community_id: UUID,
    viewer_id: UUID,
    viewer_subgroup_ids: list[UUID],
    cursor: datetime | None = None,
    limit: int = 30,
) -> list[ActivityEvent]
```

SQL (single indexed scan):

```sql
WHERE community_id = :cid
  AND is_active
  AND actor_id != :viewer_id
  AND (
        visibility = 'community'
     OR (visibility = 'subgroup' AND subgroup_id = ANY(:vsgs))
  )
  AND (cursor IS NULL OR created_at < :cursor)
ORDER BY created_at DESC
LIMIT :limit
```

Then `BaseRepository.apply_block_filter(stmt, viewer_id)` drops events
whose actor is blocked by the viewer.

### Read-time existence check

Hybrid visibility (Q3 in brainstorm): after the SQL fetch, batch
existence check per `(object_type, object_id)`:

```python
type_to_ids = group_events_by_object_type(events)
existing = {
    "post": await post_repo.exists_many(ids),
    "event": await event_repo.exists_many(ids),
    ...
}
# Drop events whose object_id is missing from existing[object_type].
```

Catches deletions where `invalidate()` was missed.

### Read-time aggregation (60-min window)

After fetch, walk the (already DESC-ordered) list and collapse
runs of consecutive same `(actor_id, verb, target_type, target_id)`
with `created_at` deltas ≤ 60 min into a single rendered item with
`count`. Newest event in the run defines the displayed timestamp.

### API endpoint

`GET /api/v1/home/activity?cursor=<iso8601>&limit=30`

Response (`ActivityFeedResponse`):

```python
class ActivityItem(BaseModel):
    id: UUID                       # newest event in aggregate
    actor_id: UUID
    actor_name: str                # from metadata snapshot
    verb: str
    object_type: str
    object_id: UUID                # for click-through link resolution
    container_type: str | None     # 'subgroup' | 'community' | None
    container_title: str | None
    object_title: str | None
    count: int                     # 1 unless aggregated
    created_at: datetime           # newest event in aggregate

class ActivityFeedResponse(BaseModel):
    items: list[ActivityItem]
    next_cursor: datetime | None
```

### Frontend

- `frontend/hooks/useActivityFeed.ts` — React Query infinite query
  keyed by `cursor`.
- `frontend/components/home/widgets/ActivityWidget.tsx` —
  rewritten to consume `useActivityFeed` instead of
  `listNotifications`. Renders each item via
  `formatActivity(item)` (a verb-keyed template lookup), with a
  click-through `resolveObjectRoute(item.object_type, item.object_id)`
  helper that returns `/app/posts/{id}`, `/app/events/{id}`, etc.
- Test: `useActivityFeed.test.ts`, `ActivityWidget.test.tsx`.

## Retention

Daily Celery beat job `prune_activity_events`:

```sql
DELETE FROM activity_event WHERE created_at < NOW() - INTERVAL '30 days';
```

Beat schedule: append to `tasks/celery_app.py:beat_schedule`. Queue:
`maintenance`.

## Community-Level Scope (the second goal)

### Backend audit

| Domain | Read aggregation | Create flow |
|---|---|---|
| Posts | `post_repo.list_feed` already unions community-root + viewer's subgroups (visibility predicate already correct). | `PostCreate` schema accepts null `subgroup_id`. |
| Events | Verify `home_service.upcoming_events` calls `event_repo.list_in_range` once with `subgroup_ids=viewer's`, not per-subgroup looped. | Verify `EventCreate` accepts null `subgroup_id` and validates `visibility ∈ {community, subgroup, private}`. |
| Galleries | Add `gallery_repo.list_aggregated(community_id, viewer_subgroup_ids, ...)` for community-root + subgroup union. | Verify `GalleryCreate` accepts null `subgroup_id`. |
| Media | Replace per-subgroup loop in `home_service.list_media` with a single `subgroup_media_repo.list_aggregated(community_id, viewer_subgroup_ids, ...)` that unions community-root + subgroup-scoped media. | n/a — media inherits scope from its source post/gallery/event. |
| Chat | Verify `chat_channel_repo.list_for_user` returns `channel_type='community'` channels for all members. | On first community boot or migration, auto-create a default `ChatChannel(channel_type='community', subgroup_id=null, name='General')`. |

### Frontend `ScopeSelect` component

New: `frontend/components/ui/ScopeSelect.tsx`. Three radio options:

```
○ Community     — visibility='community', subgroup_id=null
○ A specific group ▾  — visibility='subgroup', subgroup_id=<chosen>
○ Just me (private)  — visibility='private', subgroup_id=null
```

Wired into `PostComposer`, `EventCreateModal`, `GalleryCreateModal`,
and a future `ChannelCreateModal`. Existing modals already exposing
some of these options get refactored to use the shared control.

### Home widget scope toggle

`MediaCarouselWidget` and `ActivityWidget` scope dropdown:

```
All       → community-root + viewer's subgroups
Community → community-root only (subgroup_id IS NULL)
Subgroup  → pick one of viewer's subgroups
```

`personal` option dropped from this surface (still available on /me views).

## Files Modified / Added

**Backend (new):**
- `app/repositories/activity_repo.py`
- `app/services/activity_service.py`
- `app/api/v1/home_activity.py` (mounted on the existing home router)
- `app/schemas/activity.py`
- `app/models/activity_event.py`
- `alembic/versions/<sha>_add_activity_event.py`
- `tests/unit/repositories/test_activity_repo.py`
- `tests/unit/services/test_activity_service.py`
- `tests/unit/api/test_home_activity_api.py`

**Backend (modified):**
- `app/services/post_service.py` (handles `post.created`,
  `post.commented` — comments live on `PostService.add_comment` —
  and `post.reacted` via `toggle_comment_reaction` /
  post-reaction handlers), `event_service.py`
  (`event.created`, `event.rsvp`), `gallery_service.py`
  (`gallery.created`), `media_service.py` (`media.uploaded`),
  `chat_service.py` (`chat.posted`, sampled),
  `subgroup_member_service.py` (`member.joined`),
  `subgroups/crud.py` (`subgroup.created`), `prompt_service.py`
  (`prompt.responded`, fired when a user submits a prompt response /
  interest answer) — each gains one `activity_repo.record(...)` call
  after commit and one `activity_repo.invalidate(...)` call in delete
  paths.
- `app/services/home_service.py` — `list_media` rewritten as union;
  `upcoming_events` audited.
- `app/repositories/subgroup_media_repo.py` — add `list_aggregated`.
- `app/repositories/gallery_repo.py` — add `list_aggregated`.
- `app/tasks/celery_app.py` — append `prune_activity_events` to
  `beat_schedule`.

**Frontend (new):**
- `hooks/useActivityFeed.ts`
- `components/ui/ScopeSelect.tsx`
- Tests: `hooks/useActivityFeed.test.ts`,
  `components/ui/ScopeSelect.test.tsx`,
  `components/home/widgets/ActivityWidget.test.tsx` (rewrite).

**Frontend (modified):**
- `components/home/widgets/ActivityWidget.tsx` — replace notifications
  source with `useActivityFeed`.
- `components/home/widgets/MediaCarouselWidget.tsx` — drop `personal`
  scope; verify "All" / "Community" / "Subgroup" options work against
  the new union endpoint.
- `components/feed/PostComposer.tsx`,
  `components/events/EventCreateModal.tsx`,
  `components/galleries/GalleryCreateModal.tsx` — adopt `ScopeSelect`.
- `lib/api/home.ts` — add `getHomeActivity({ cursor, limit })`.

## Testing & Verification

### Backend

- `test_activity_repo.py` — record/list/invalidate; visibility filter
  per case (community / subgroup / private); block filter applied;
  cursor pagination; retention DELETE.
- `test_activity_service.py` — read-time aggregation
  (4 photos in 60 min → 1 item count=4; 4 photos > 60 min apart → 4
  items); own-actions excluded; dead-object filter.
- Per-domain `test_<X>_service.py` — assert
  `activity_repo.record` called with correct verb + visibility on
  each create path; `invalidate()` called on each delete.
- `test_home_service.py` — `list_media` returns community-root +
  subgroup union; `scope='community'` returns only
  `subgroup_id IS NULL`; `scope='all'` returns both.
- `test_home_activity_api.py` — endpoint smoke + auth.

### Frontend

- `useActivityFeed.test.ts` — pagination, error, refetch.
- `ActivityWidget.test.tsx` — verb formatting per type, click-through
  routing, empty/loading/error states.
- `ScopeSelect.test.tsx` — emits correct `{visibility, subgroup_id}`
  for each option.
- Updated `MediaCarouselWidget.test.tsx` — drop `personal`, exercise
  union behaviour.

### Manual

1. Create a community-root post, gallery, and event (no subgroup) →
   each appears in home feed / media widget / upcoming events.
2. Sue posts in "Family" subgroup → John (also in Family) sees
   "Sue posted in Family". Sue herself does not see it.
3. Upload 5 photos in ≤60 min → 1 row "Sue added 5 photos to
   Trip Album". After 60 min, a second batch → 2 rows.
4. Block a user → their activity drops from your feed within one
   refetch.
5. Delete a post → its `post.created` activity row vanishes
   (`is_active=false`).
6. Manually backdate an activity row to 31 days ago → daily prune
   job removes it.

## Out of Scope

- Activity-driven push/email notifications (existing
  `notifications` pipeline stays).
- Full-text search across activity.
- Cross-verb aggregation ("Sue posted and uploaded photos").
- Per-user feed personalization (relevance ranking, ML).
- An admin UI for muting verbs.

## Phasing (suggested)

1. **Schema + repo + retention job** — migration, `activity_repo`,
   beat job, tests.
2. **Domain wiring (writes)** — every service gets
   `record()` + `invalidate()`. One commit per ~3 services to keep
   reviews tight.
3. **API + frontend hook + widget rewrite** — endpoint, hook,
   `ActivityWidget` rewrite + tests.
4. **Community-scope aggregator fixes** — `home_service.list_media`
   union, `gallery_repo.list_aggregated`, `events` audit.
5. **`ScopeSelect` + create-flow refactors** — shared control,
   modal updates.
6. **Default community chat channel** — migration / boot hook.
