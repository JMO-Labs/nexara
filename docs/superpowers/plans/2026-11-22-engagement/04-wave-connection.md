# Wave 4 — Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirmed relations, family + group tree, reconnect nudges, safe arrival, voice stories.

**Architecture:** Task 1 (relations) first; Tasks 2 and 3 depend on it. Tasks 4 and 5 are independent and may run in parallel with 1. Then polish.

**Spec:** `00-overview.md`. **Branch:** `feat/eng-w4-connection` from `feat/eng-w3-practical`.

---

### Task 1: Relations

**Files:**
- Create: `backend/alembic/versions/0060_relations.py`, `backend/app/models/relation.py`, `backend/app/repositories/relation_repo.py`, `backend/app/schemas/relation.py`, `backend/app/services/relation_labels.py`, `backend/app/services/relation_service.py`, `backend/app/api/v1/relations.py`, `backend/app/services/notifications/types/relation_request.py`, `frontend/lib/api/relations.ts`, `frontend/components/relations/{RelationsCard,AddRelationDialog,RelationRequests}.tsx`
- Modify: profile About tab (RelationsCard), settings field visibility (+`relations`, default `community`), `memorial_service.set_passed_on` (allow confirmed relatives)
- Test: `backend/tests/unit/services/test_relation_labels.py`, `backend/tests/unit/services/test_relation_service.py`, frontend dialog test

**Interfaces:**
- Table `relations(id, community_id, from_user_id, to_user_id null, to_household_member_id null, kind text check in ('parent','child','spouse','partner','sibling','friend','other'), label text null ≤40 (for 'other'), status text check in ('pending','confirmed'), created_by, created_at, confirmed_at null)`; check exactly one `to_*`; unique on (from, to_user) and (from, to_household) regardless of direction (unique index on `least/greatest` pair for user↔user).
- Meaning: `from` is `<kind>` of `to` ("Ruth is parent of Dana"). `inverse(kind)`: parent↔child; others symmetric.
- `relation_labels.derive(path: list[str], pronouns: str | None) -> str` — path of base kinds from viewer outward: `[parent,parent]`→grandparent; `[parent,sibling]`→aunt/uncle; `[parent,sibling,child]`→cousin; `[sibling,child]`→niece/nephew; `[spouse,parent]`→parent-in-law; `[child,child]`→grandchild; pronouns `she/*`→female word, `he/*`→male word, else neutral ("aunt or uncle", "niece or nephew", "grandparent"). Unknown path → "relative".
- Service: `request(actor, to_user|to_member, kind, label)` — user target → pending + notify; household target → owner only, auto-confirmed. `confirm(id, actor)` (target only), `remove(id, actor)` (either side or admin), `list_for(user_id, viewer_id)` honoring field visibility `relations`, `is_confirmed_relative(a, b) -> bool` (direct family kinds only, not friend/other), `graph(community_id) -> list[Relation]` (confirmed only; used by tree + nudges).
- Excludes memorialized users as request targets (they can only be linked by admin).
- [ ] Tests: derive cases above incl. pronoun variants; duplicate in reverse direction → 409; Maya confirms → both see it with inverse label; third party can't confirm; field visibility `only_me` hides list from others; blocked user can't request.
- [ ] Implement → PASS → commit `feat(relations): confirmed family and friend relations`

---

### Task 2: Family tree + group tree

**Files:**
- Create: `backend/app/services/tree_service.py`, `backend/app/api/v1/tree.py`, `backend/app/schemas/tree.py`, `frontend/lib/tree/layout.ts`, `frontend/components/tree/{FamilyTree,TreeNode,TreeList,TreeControls}.tsx`, `frontend/app/app/family/page.tsx`
- Modify: group page tabs (+Tree), nav (`Network` icon, label "Family")
- Test: `backend/tests/unit/services/test_tree_service.py`, `frontend/tests/unit/lib/tree/layout.test.ts`, `frontend/tests/unit/components/tree/FamilyTree.test.tsx`

**Interfaces:**
- Consumes: `RelationService.graph`, household members (`kind='person'`), `passed_on`, `memorialized_at`, field visibility.
- `TreeNode{id: str ("u:<uuid>"|"h:<uuid>"|"p:<n>"), name, avatar_url, kind: "user"|"household"|"private", memorial: bool, link: str|null}`; `TreeEdge{a, b, kind: parent|spouse|partner|sibling|friend|other|via_family}` (parent edges point parent→child).
- `GET /api/v1/tree/family?root=<user_id>&gens=3` — BFS from root over confirmed relations up to `gens` generations each way (cap 300 nodes; response `truncated: bool`); nodes the viewer may not see (relations visibility or household visibility) become `kind="private"`, name "Private relative", no link; edges to them kept.
- `GET /api/v1/tree/group/{slug}` — only group members (viewer must be member); edges among members; for member pairs with no direct edge but a path ≤4 hops through non-members → one `via_family` edge, intermediates never returned.
- `layout.ts`: `layoutTree(nodes, edges, opts{showFriends}) -> {positions: Record<id,{x,y}>, width, height}` — generation = longest parent-chain depth (spouses/partners share generation), rows by generation, spouses adjacent, order within row by one barycenter pass over parents; disconnected components placed side by side; unlinked nodes returned in `loose: string[]`.
- UI: SVG with pan (pointer drag) + zoom (wheel, +/− buttons), nodes are `<a>`/`<button>` with focus ring; Tab order follows rows; "Show friends" toggle (default off on family page, on in group tab); "List view" toggle renders `TreeList` (nested `<ul>`, screen-reader default via `aria` description); memorial nodes muted with dates; "Expand" button when `truncated`.
- [ ] Tests: service — private node hides name; group tree omits outsider, adds `via_family`; cap 300 sets truncated. Layout — grandparent y < parent y < child y; spouses same y, adjacent x; two disconnected families don't overlap; friend edges excluded when `showFriends=false`.
- [ ] Implement → PASS → commit `feat(tree): family tree and group relationship tree`

---

### Task 3: Reconnect nudges

**Files:**
- Create: `backend/alembic/versions/0061_reconnect.py`, `backend/app/services/reconnect_service.py`, `backend/app/services/notifications/types/reconnect.py`
- Modify: `backend/app/repositories/nudge_repo.py` (+queries), `backend/app/tasks/nudge_tasks.py` (+task), `celery_app.py`, notification settings UI (toggle + days select 14/30/60/90), notification item actions (Message · Snooze 90 days)
- Test: `backend/tests/unit/services/test_reconnect_service.py`

**Interfaces:**
- `user_settings.reconnect_nudges bool default true`, `reconnect_days int default 30 check in (14,30,60,90)`; table `reconnect_snoozes(user_id, target_id, until timestamptz, pk both)`; nudge rows use existing `nudges` table with `nudge_type='reconnect'`.
- `ReconnectService.pick(user_id, now) -> UUID | None` — confirmed family (`is_confirmed_relative`), active, not memorialized, not blocked, not snoozed; last interaction = max(DM message between them, comment by user on target's post or vice versa, kudos either way); candidate if older than `reconnect_days`; choose the longest gap; None if user got a reconnect nudge in last 7 days.
- Beat daily `nudges.reconnect` at 15:00 UTC (ponytail: fixed hour; per-tz later if asked). `POST /api/v1/reconnect/snooze {target_id}` → 90 days.
- [ ] Tests: no interaction 40 days → picked; DM 10 days ago → not; friend relation → never; snoozed → skipped; nudge 3 days ago → None; running twice → one notification.
- [ ] Implement → PASS → commit `feat(nudges): private reconnect reminders for family`

---

### Task 4: Safe arrival

**Files:**
- Create: `backend/alembic/versions/0062_trips.py`, `backend/app/models/trip.py`, `backend/app/repositories/trip_repo.py`, `backend/app/schemas/trip.py`, `backend/app/services/trip_service.py`, `backend/app/api/v1/trips.py`, `backend/app/tasks/trip_tasks.py`, notif types `trip_started.py`, `trip_overdue.py`, `trip_arrived.py`, `frontend/lib/api/trips.ts`, `frontend/components/trips/{StartTripDialog,ActiveTripBar,WatchingChips}.tsx`
- Modify: top bar (ActiveTripBar while traveling: "Made it" button + extend), Home People tile (watching chips), `celery_app.py`
- Test: `backend/tests/unit/services/test_trip_service.py`, `backend/tests/unit/tasks/test_trip_tasks.py`, frontend tests

**Interfaces:**
- Tables: `trips(id, community_id, user_id, label ≤80, expected_at timestamptz, arrived_at null, alerted_at null, ended_at null, created_at)`, `trip_watchers(trip_id fk cascade, user_id, pk both)`; one active trip per user (partial unique where `arrived_at IS NULL AND ended_at IS NULL`).
- Service: `start(user, label, expected_at (now+10min..now+72h), watcher_ids 1..20 not blocked)` → notify watchers `trip_started`; `extend(trip, user, new_expected)` (clears `alerted_at`); `arrive(trip, user)` → notify `trip_arrived`; `cancel`.
- Beat every 5 min: overdue = `now > expected_at + 1h`, not arrived, `alerted_at IS NULL` → notify `trip_overdue` (push + inapp default on, ignores digest batching: register with `group_window_seconds=None`, toast on), stamp; auto-end where `now > expected_at + 24h` → `ended_at=now`.
- No location stored.
- [ ] Tests: expected in 5 min → 422; overdue alert once across two runs; extend after alert → can alert again; arrive notifies watchers; auto-end at +24h; second active trip → 409.
- [ ] Implement → PASS → commit `feat(trips): made-it-home check-ins with overdue alert`

---

### Task 5: Voice stories

**Files:**
- Create: `backend/alembic/versions/0063_stories.py`, `backend/app/models/story_request.py`, `backend/app/repositories/story_repo.py`, `backend/app/schemas/story.py`, `backend/app/services/story_service.py`, `backend/app/api/v1/stories.py`, `backend/app/tasks/story_tasks.py`, `backend/data/story_questions.json` (100 entries), notif types `story_request.py`, `story_answered.py`, `frontend/components/audio/{Recorder,AudioPlayer}.tsx`, `frontend/components/stories/{AskStoryDialog,StoryRequests,StoriesTab}.tsx`
- Modify: `backend/app/services/storage/validation.py` (audio magic bytes), `media_service.py` (audio size 25 MB), `backend/app/tasks/media_tasks.py` (+`transcode_audio`), `backend/app/models/post.py` (+`story_request_id`), post composer (mic button → Recorder), daily question answer composer (Recorder), profile tabs (+Stories), PostCard (AudioPlayer for audio media), `recap_sections.py` (+pending story requests)
- Test: `backend/tests/unit/services/storage/test_validation_audio.py`, `backend/tests/unit/tasks/test_transcode_audio.py` (ffmpeg mocked), `backend/tests/unit/services/test_story_service.py`, frontend Recorder/AudioPlayer tests (MediaRecorder mocked)

**Interfaces:**
- Validation: `ID3` or MPEG frame sync `0xFFEx` → `audio/mpeg`; `ftyp` brands `M4A `/`M4B ` → `audio/mp4`; `OggS` → `audio/ogg`; webm header with audio-only declared type → `audio/webm`. Max 25 MB.
- `transcode_audio(media_id)`: ffmpeg → AAC 96 kbps `.m4a`, sets `duration_secs`; duration > 900 s → media status `rejected` + error `AUDIO_TOO_LONG`.
- Table `story_requests(id, community_id, asker_id, teller_id, question ≤280, status check in ('open','answered','declined','expired'), post_id null, reminded_at null, created_at, expires_at = created_at + 30 days)`; `posts.story_request_id uuid null`.
- Service: `ask(asker, teller, question)` (not self, not blocked, ≤5 open asks per asker→teller); `answer(request, teller, post_id)` (post must be teller's, has audio or text); `decline(request, teller)` — asker sees status `open` until expiry then `expired` (silent decline: API to asker maps `declined`→`open` before expiry, `expired` after). Beat daily: reminder at day 14 once, expire at day 30.
- Stories tab: posts by user with `story_request_id` or audio media, newest first, question shown above player.
- Recorder: picks `audio/mp4` if `MediaRecorder.isTypeSupported` else `audio/webm`; timer, 15-min auto-stop, retake, upload via existing media upload; mic-permission denied → message with how to enable. AudioPlayer: native `<audio controls>` + speed 1×/1.5× (ponytail: native controls do the rest).
- [ ] Tests: each magic-byte sample detected; 26 MB → 413; transcode sets duration; 16-min → rejected; asker sees `open` after decline; reminder once; expire at 30 d; answer links post and notifies asker.
- [ ] Implement → PASS → commit `feat(stories): voice recordings and story requests`

---

### Task 6: Wave polish + PR (orchestrator)

- [ ] Migrate local DBs to 0063; full suites; lint/type/format.
- [ ] Eval: Ruth↔Dana parent confirmed, Maya grandchild → tree shows 3 generations, "grandparent" label; group tree with via_family; reconnect task picks stale relative; trip overdue alert via forced clock; record a real 10-s clip in browser (Playwright fake media flag), answer story request.
- [ ] Screenshots of tree (light/dark/phone + list view), screen-reader pass on tree; `/simplify`.
- [ ] Push; PR "feat: engagement wave 4 — connection" on wave-3 PR.

---

### Task 7 (added 2026-11-22, user request): Online status indicators

Presence already exists (Valkey sorted set `services/realtime/presence.py`, set on SSE/WS connect, privacy `show_online_status` / `show_last_seen`) but only the Home people strip and member header show it, and two bugs make it wrong.

**Files:**
- Create: `backend/app/services/presence_service.py`, `backend/app/api/v1/presence.py`, `backend/app/schemas/presence.py`, `frontend/lib/api/presence.ts`, `frontend/stores/presence.ts`, `frontend/components/layout/PresenceSync.tsx`
- Modify: `backend/app/api/v1/sse.py` (+ `ws.py`) heartbeat + disconnect, `frontend/components/ui/Avatar.tsx` (`userId` prop → dot), call sites listed below
- Test: backend unit + one real-Postgres privacy test; frontend Avatar dot, store batching, path test

**Interfaces:**
- Bug 1: SSE/WS heartbeat calls `set_online(user_id)` (refresh) every heartbeat; Bug 2: on disconnect call `set_offline` only when the connection manager has no other live connection for that user.
- `POST /api/v1/presence {user_ids: list[UUID] (1..200)}` → `{online: list[UUID], last_seen: dict[UUID, datetime | None]}`. Only same-community, active, non-memorialized users; omit anyone in a block relation with the viewer; `online` only when the target's `show_online_status` is true; `last_seen` only when `show_last_seen` is true. Viewer always sees themselves.
- Frontend: `usePresenceStore` (zustand) — `watch(ids)` / `unwatch(ids)` ref-counted; `PresenceSync` (mounted once in Shell) posts the watched ids every 60 s and on SSE reconnect; `useOnline(userId) -> boolean`.
- `Avatar` gets optional `userId`; when online renders a 25%-size dot (success token, 2px ring of surface colour) bottom-right with `<span className="sr-only">online</span>`; no dot when offline (no grey dot).
- Pass `userId` at: chat thread list + conversation header + message author, post and comment authors, members directory cards, mention picker rows, profile header, Home People tile/strip (replace their bespoke dot).
- Respects the existing "Show online status" privacy toggle (already in Settings → Privacy).
