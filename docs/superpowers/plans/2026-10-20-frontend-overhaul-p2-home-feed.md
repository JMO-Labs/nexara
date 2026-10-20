# Frontend Overhaul P2 — Home + Unified Live Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Garden Club home: unified live feed (posts + activity) with server-side privacy, Next-up card, reorderable widget column — plus every component the shell and `/login` pull in, so the app is viewable in a browser at the end of this phase.

**Architecture:** Backend gains audience-scoped realtime (fixes existing SSE privacy leak), a merged `GET /api/v1/home/feed`, and a `feed_ping` SSE signal on every activity. Frontend gains `useHomeFeed` (TanStack infinite query, refetch head on `feed_ping`), `HomeFeed`, `ActivityLine`, `NextUpCard`, `WidgetColumn` (dnd-kit). Chat dock children, PostComposer, Event/Gallery create modals and the login page are re-skinned so `/login` and `/app` compile with zero Joy.

**Tech Stack:** FastAPI + SQLAlchemy 2 async, pytest; Next.js 16 / React 19, Tailwind v4 + shadcn (`components/ui`), TanStack Query v5, dnd-kit (installed), framer-motion, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-20-frontend-overhaul-design.md` (§5, §6, §11) · **Index:** `…-frontend-overhaul-index.md` · **P1 plan (Global Constraints):** `…-p1-foundation-shell.md`

## Global Constraints

- All P1 Global Constraints apply (tokens, Hanken Grotesk, Lucide, AA, reduced motion, ≤400 lines, Doxygen headers, sentence case).
- Frontend: read the relevant guide in `frontend/node_modules/next/dist/docs/` before using any Next API (`frontend/AGENTS.md`: Next 16 has breaking changes).
- Frontend primitives come from `@/components/ui` (barrel); raw shadcn in `components/ui/shadcn/`. No new npm deps.
- Untrusted links: use `safeInternalLink()` from `@/lib/safeLink`. API path params: `seg()` from `@/lib/api/client`.
- Backend: strict layering router → service → repo; every query filters `community_id`; viewer reads call `apply_block_filter`; errors via `core/exceptions.py`; `ruff check`, `ruff format --check`, `pytest` pass for touched code. Tests need Postgres on `localhost:5432` (nexara/nexara/nexara; test DB `nexara_test` exists).
- Branch: `feat/fo-p2-home-feed` (from `feat/frontend-overhaul`). Commit messages per task, ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Subgroup/private item reaching a non-member** over SSE or the feed endpoint — Task 1 and Task 2 tests assert exclusion.
2. **Blocked user's activity visible** (either direction) — Task 1 resolver test + Task 2 feed test.
3. **Reader scrolled down while 3 items arrive** — nothing shifts; pill reads "3 new"; tapping scrolls to top and reveals them. Task 6 test.
4. **Cursor tie at identical `created_at`** — paging must not repeat items. Task 2 test (dedupe by id across pages; ponytail: timestamp cursor, ties at the boundary may skip; compound cursor if seen).
5. **Old grid-shaped `home_layout`** stored for a user — loads default order, no crash. Task 2 + Task 7 tests.

---

## Wave plan

| Wave | Tasks (parallel within wave) |
|---|---|
| W1 | 1 (BE audience), 2 (BE feed + layout schema), 4 (feed cards + ActivityLine), 5 (PostComposer), 8 (chat dock children), 9 (create modals), 10 (login) |
| W2 | 3 (BE feed_ping, needs 1), 6 (useHomeFeed + HomeFeed, needs 2/4/5), 7 (widget column + hook, needs 2) |
| W3 | 11 (home page assembly: needs 6/7) |
| W4 | 12 (gate) |

---

### Task 1: Audience-scoped realtime (BE)

**Files:** Create `backend/app/services/realtime/audience.py`; Modify `backend/app/services/realtime/events.py`, call sites of `post_created` / `comment_created` / reaction / poll builders (`backend/app/services/post_service.py` and any others found by grep); Test `backend/tests/unit/services/realtime/test_audience.py`, update existing event tests.

**Interfaces:**
- Produces `async def resolve_audience(session: AsyncSession, community_id: UUID, *, visibility: str, subgroup_id: UUID | None, author_id: UUID) -> list[UUID]`:
  `community` → all active community members; `subgroup` → `SubgroupMember` user_ids of that subgroup; `private` → `[author_id]`. Always includes `author_id`. Excludes any user with a block relation with the author in either direction (use the existing block model the repos' `apply_block_filter` uses).
- Produces `async def emit_to_audience(event_bus, audience: list[UUID], type: EventType, payload: dict) -> None` (one `RealtimeEvent` per `UserTarget`).
- Existing `feed_update` builders take a `target: EventTarget` instead of hard-coding `CommunityTarget`; callers emit via `emit_to_audience` with the post's visibility/subgroup/author.

- [ ] Step 1: Tests: private post → `[author]`; subgroup post → members only (non-member absent); community → all members; user who blocked the author (and user the author blocked) absent; post_service create emits only to resolved audience (mock event_bus, assert targets).
- [ ] Step 2: `pytest tests/unit/services/realtime/test_audience.py -x` → FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: `pytest -q` (full backend) → PASS; ruff clean.
- [ ] Step 5: Commit `fix(realtime): scope feed events to permitted audience`.

### Task 2: Unified home feed endpoint + layout schema (BE)

**Files:** Create `backend/app/services/home_feed_service.py`, `backend/app/schemas/home_feed.py`; Modify `backend/app/api/v1/home.py` (route), `backend/app/services/activity_service.py` (window param), `backend/app/schemas/settings.py` + `backend/app/services/settings_service.py` (home_layout shape); Test `backend/tests/unit/services/test_home_feed_service.py`, `backend/tests/unit/api/test_home_feed_api.py`, update `backend/tests/unit/api/test_user_settings_home_layout.py`.

**Interfaces:**
- `GET /api/v1/home/feed?cursor=<str>&limit=<1..50, default 20>` → `HomeFeedResponse { items: list[FeedItem]; next_cursor: str | None }`.
- `FeedItem` (discriminated on `kind`): `{ kind: "post", id: UUID, created_at: datetime, post: dict }` (post = same enriched dict `GET /posts` returns) | `{ kind: "activity", id: UUID, created_at: datetime, activity: ActivityItem }` (existing schema).
- `HomeFeedService.list(viewer: User, cursor: str | None, limit: int) -> HomeFeedResponse`: fetch `limit` posts via `post_repo.list_feed` (viewer-scoped) and `limit` activity via `ActivityService.list_for_user(..., window_seconds=10)`; drop activity with verb `post.created` (the post card represents it); merge by `created_at` desc; take `limit`; `next_cursor` = ISO `created_at` of last item; dedupe by `(kind,id)`.
- `ActivityService.list_for_user(..., window_seconds: int = 3600)` — aggregation window parameterized; existing behavior unchanged by default.
- `home_layout` setting becomes `{ order: list[str], hidden: list[str] }` (widget ids: `"upcoming-events"`, `"my-groups"`, `"media"`, `"quick-actions"`). Reading a stored value of any other shape returns `{ order: [default order], hidden: [] }`.

- [ ] Step 1: Tests: merge order; `post.created` activity excluded; subgroup post + its activity absent for non-member; blocked actor absent; two pages with `limit=2` over 5 items return 5 distinct ids; legacy `{widgets:[{x,y,w,h}]}` layout reads as default; PUT new shape round-trips.
- [ ] Step 2: run → FAIL. Step 3: implement. Step 4: `pytest -q` → PASS; ruff clean.
- [ ] Step 5: Commit `feat(home): unified feed endpoint and list-shaped widget layout`.

### Task 3: `feed_ping` on every activity (BE, after Task 1)

**Files:** Create `backend/app/services/activity_publish.py`; Modify every service call site of `ActivityRepository.record(` (≈10, grep) ; Modify `backend/app/services/realtime/events.py` (`EventType.FEED_PING = "feed_ping"`); Test `backend/tests/unit/services/test_activity_publish.py`.

**Interfaces:**
- `async def record_activity(activity_repo, session, event_bus, **record_kwargs) -> ActivityEvent` — calls `activity_repo.record(**record_kwargs)`, then `emit_to_audience(event_bus, await resolve_audience(...visibility, subgroup_id, actor_id as author), EventType.FEED_PING, {"at": created_at.isoformat()})`. Emission failure is logged, never raised.
- All existing `activity_repo.record(` call sites in services switch to `record_activity(`.

- [ ] Step 1: Tests: records then pings audience only; emit exception does not propagate; grep-based test or review confirms no direct `.record(` left in `app/services` except inside `activity_publish.py`.
- [ ] Steps 2–4: FAIL → implement → `pytest -q` PASS.
- [ ] Step 5: Commit `feat(realtime): feed_ping to audience on every activity`.

### Task 4: Feed cards + ActivityLine (FE)

**Files:** Rewrite `frontend/components/feed/{PostCard,PostHeader,PostBody,PostMedia,SourceBadge,PromptPostCard,ReactionRow,CommentThread}.tsx`; Create `frontend/components/feed/ActivityLine.tsx`; Rewrite/extend matching tests under `frontend/tests/unit/feed/`.

**Interfaces:**
- Public props of the rewritten components unchanged (callers keep working).
- `PostCard`: `Card` default tone, `rounded-[1.25rem]`; poll posts keep current poll rendering, re-skinned.
- `ActivityLine({ item }: { item: ActivityItem })` — one line: `Avatar` (sm, `item.actor_name`), sentence, relative time (`<time dateTime>`). Sentences: `post.commented` "{actor} commented on {object_title}", `post.reacted` "{actor} reacted to {object_title}", `event.rsvp` "{actor} is going to {object_title}", `subgroup.joined` "{actor} joined {container_title}", `media.uploaded` "{actor} added {count} photos" (count>1) / "a photo"; unknown verb → "{actor} was active". Count > 1 for other verbs appends " ({count})". Whole line links to the object when a route exists (post → `/app/post/{id}`, event → `/app/events?event={id}`, subgroup → `/app/subgroups/{slug}` only if slug present in item, else no link). Check `ActivityItem` type in `hooks/useActivityFeed.ts` / `lib/api/home.ts` for exact fields and verb strings used by the backend; use the backend's real verb names.

- [ ] Step 1: tests: each verb sentence; unknown verb fallback; link href for post; existing PostCard/ReactionRow/CommentThread behavior tests kept (drop Joy markup assertions).
- [ ] Steps 2–4: FAIL → implement → `npx vitest run tests/unit/feed` PASS; eslint clean.

### Task 5: PostComposer (FE)

**Files:** Rewrite `frontend/components/feed/PostComposer.tsx` (Tiptap kept; split into `PostComposer.tsx` + `ComposerToolbar.tsx` if >400 lines); tests `frontend/tests/unit/feed/PostComposer.test.tsx`.

**Interfaces:** props unchanged. Visibility via `ScopeSelect`; submit `Button` labelled "Post"; toast "Posted". Interest/subgroup chips via `Chip` with children (not `label`).

- [ ] Steps: test (existing behavior + visibility payload + chip text visible) → FAIL → implement → PASS.

### Task 6: `useHomeFeed` + `HomeFeed` (FE, after 2/4/5)

**Files:** Modify `frontend/lib/api/home.ts`, `frontend/lib/query-keys.ts`; Create `frontend/hooks/useHomeFeed.ts`, `frontend/components/home/HomeFeed.tsx`, `frontend/components/home/NewItemsPill.tsx`; Tests `frontend/tests/unit/hooks/useHomeFeed.test.tsx`, `frontend/tests/unit/components/home/HomeFeed.test.tsx`.

**Interfaces:**
- `getHomeFeed(cursor?: string): Promise<HomeFeedResponse>`; types `FeedItem`, `HomeFeedResponse` mirroring Task 2.
- `qk.home.feed()` key.
- `useHomeFeed(): { items: FeedItem[]; fetchNextPage; hasNextPage; isLoading; pending: FeedItem[]; reveal: () => void }` — `useInfiniteQuery`. On SSE `feed_ping` (subscribe via existing `hooks/useSSE.ts` API) fetch head page (`getHomeFeed()`); items whose `kind:id` is not in current items go to `pending`. If `atTop` (window scrollY < 120) reveal immediately; else keep in `pending`. `reveal()` prepends pending to the first page cache and clears it. Existing `feed_update` events also trigger the head refetch.
- `HomeFeed()`: `PostComposer` at top; list rendering `PostCard` for posts, `ActivityLine` for activity; newly revealed items get `data-new="true"` and a 2s lilac ring (`motion-safe` only); `NewItemsPill` (`{count, onClick}`, button text "{count} new", fixed under top bar, `aria-live="polite"`) when `pending.length > 0`; clicking scrolls to top then `reveal()`; infinite scroll via IntersectionObserver sentinel; `EmptyState` "Nothing here yet" with action "Write the first post" focusing the composer.

- [ ] Step 1: tests: renders mixed items in order; ping while scrolled (mock scrollY=800) → pill "2 new", list unchanged; click pill → items prepended, pill gone; ping at top → items inserted with `data-new`; sentinel triggers `fetchNextPage`.
- [ ] Steps 2–4: FAIL → implement → PASS.

### Task 7: Widget prefs hook + WidgetColumn (FE, after 2)

**Files:** Rewrite `frontend/hooks/useHomeLayout.ts`; Create `frontend/components/home/WidgetColumn.tsx`, `frontend/components/home/widgetRegistry.tsx`; Rewrite `frontend/components/home/widgets/{UpcomingEventsWidget,MyGroupsWidget,MediaCarouselWidget,QuickActionsWidget}.tsx`, `frontend/components/home/WidgetFrame.tsx` (simple titled `Card`, collapse removed); Delete `WidgetGrid.tsx`, `WidgetGallery.tsx`, `RightRail.tsx`, `widgets/FeedWidget.tsx`, `widgets/ActivityWidget.tsx`, `stores/dashboardRail.ts`, `stores/widgetDrag.ts`, `hooks/useActivityFeed.ts` (if unused after this) and their tests; remove RightRail mock from `tests/unit/layout/Shell.test.tsx`. Tests: `frontend/tests/unit/hooks/useHomeLayout.test.tsx`, `frontend/tests/unit/components/home/WidgetColumn.test.tsx`, rewrite widget tests.

**Interfaces:**
- `WIDGETS: { id: WidgetId; title: string; Component: ComponentType }[]` in `widgetRegistry.tsx`, `type WidgetId = "upcoming-events" | "my-groups" | "media" | "quick-actions"`, default order as listed.
- `useHomeLayout(): { order: WidgetId[]; hidden: WidgetId[]; move(from: number, to: number): void; toggle(id: WidgetId): void }` — reads/writes settings `home_layout` `{order, hidden}`; unknown ids dropped, missing ids appended; non-matching shape → defaults. Optimistic, debounced PUT 500ms.
- `WidgetColumn()`: `aside aria-label="Widgets"`, `hidden md:flex flex-col w-[300px] gap-4`; dnd-kit `SortableContext` vertical with keyboard sensor (space to lift, arrows to move — dnd-kit KeyboardSensor + `sortableKeyboardCoordinates`); each widget has a drag handle `IconButton aria-label="Reorder {title}"`; footer "Customize" dropdown (shadcn `dropdown-menu`) with a checkbox item per widget to show/hide.

- [ ] Step 1: tests: hook legacy-shape → defaults; move updates order and PUTs; toggle hides; column renders visible widgets in order; keyboard reorder moves item; hidden widget absent and re-shown via Customize.
- [ ] Steps 2–4: FAIL → implement → PASS.

### Task 8: Chat dock children (FE)

**Files:** Rewrite `frontend/components/chat/{ChatHead,ChatLauncher,MessageList,MessageItem,Composer,TypingIndicator}.tsx`; Modify `frontend/components/chat/FloatingChatDock.tsx` (static imports again instead of `next/dynamic`); tests under `frontend/tests/unit/chat/` and `frontend/tests/unit/components/chat/` covering these (drop stubs).

**Interfaces:** props unchanged. Message bubbles: own `bg-surface-strong text-bg`, others `bg-surface`; leaf corner on the sender side. Composer send `IconButton aria-label="Send message"`. Do NOT touch `ChannelList`, `ChatLayout`, `NewDmModal` (P3).

- [ ] Steps: tests (send, typing indicator text, launcher opens head, message list renders) → FAIL → implement → PASS.

### Task 9: Event + gallery create modals (FE)

**Files:** Split + rewrite `frontend/components/events/EventCreateModal.tsx` (609) into `EventCreateModal.tsx` + `event-form/*.tsx` sections each ≤400 lines; rewrite `frontend/components/galleries/GalleryCreateModal.tsx` and its transitive Joy/@emotion imports (e.g. `GalleryUpload.tsx`) — find with `grep -l "@mui\|@emotion\|@heroicons"` over each import chain; tests `frontend/tests/unit/components/EventCreateModal.test.tsx`, gallery modal tests.

**Interfaces:** props unchanged; built on `Modal` (phone: bottom sheet). Native `<input type="date">`/`type="time"` for date/time unless an existing picker component is already used — then re-skin it. Map picker (Leaflet) kept, re-skinned frame only.

- [ ] Steps: existing behavior tests kept (submit payload, validation messages) → FAIL → implement → PASS. Report every extra file touched.

### Task 10: Login page (FE)

**Files:** `frontend/app/(auth)/layout.tsx` (if present), `frontend/app/(auth)/login/page.tsx` and every component it imports that uses Joy (e.g. under `frontend/components/auth/`); tests under `frontend/tests/unit/` covering login/auth-flow.

**Interfaces:** behavior unchanged (password, magic link, OAuth buttons, 2FA redirect). Layout: `bg-bg`, centered `Card` max-w-sm on phone full-width; community name in Hanken 900. Other auth routes stay for P6 unless they share these components (then they get the new look for free).

- [ ] Steps: tests (submit calls login, error shown via `Input error`, OAuth buttons render from config) → FAIL → implement → PASS.

### Task 11: Home page assembly (FE, after 6/7)

**Files:** Rewrite `frontend/app/app/page.tsx`, `frontend/components/home/WelcomeBanner.tsx` → greeting; Create `frontend/components/home/NextUpCard.tsx`; Tests `frontend/tests/unit/app/home-page.test.tsx` (rewrite off Joy), `frontend/tests/unit/components/home/NextUpCard.test.tsx`.

**Interfaces:**
- Page: greeting `h1` (Hanken 900, `text-4xl md:text-5xl`, tight leading): "Hi {firstName}." + day-part line above in `text-muted` ("Tuesday evening"); then phone: `NextUpCard` → `HomeFeed`; desktop (≥ md): two columns — `HomeFeed` (`max-w-2xl`) + `WidgetColumn`. `NextUpCard` shown on desktop too, above the feed.
- `NextUpCard()`: `Card tone="featured"`; date chip `bg-accent text-surface-strong rounded-2xl` (day number 900 + weekday short); title + location + "{n} going". Selection: nearest upcoming event the viewer RSVP'd yes/maybe; else nearest visible upcoming event; else render nothing. Data from existing hooks (`useHomeSummary` / `useEvents` — use whichever already returns upcoming events with the viewer's RSVP).

- [ ] Steps: tests (greeting, NextUp selection rules ×3, desktop has `Widgets` aside) → FAIL → implement → PASS.

### Task 12: Gate

- [ ] Step 1: `cd frontend && npx vitest run tests/unit/ui tests/unit/layout tests/unit/theme tests/unit/lib tests/unit/app tests/unit/feed tests/unit/chat tests/unit/components tests/unit/hooks tests/unit/search tests/unit/notifications` → PASS (list any remaining failures with cause; failures are allowed only in areas owned by P3–P7).
- [ ] Step 2: `npx eslint app/app/page.tsx 'app/(auth)' components/home components/feed components/chat components/events/EventCreateModal.tsx components/events/event-form components/galleries hooks lib` → 0 errors.
- [ ] Step 3: Import-graph check: `npx next dev` in background, then `curl -s -o /dev/null -w "%{http_code}" localhost:3000/login` and `/app` → `200`, and the dev server log shows no "Module not found". Stop the server.
- [ ] Step 4: `cd backend && ruff check . && ruff format --check . && pytest -q` → PASS.
- [ ] Step 5: Update index (P2 done; note P3 loses chat dock children, P4 loses EventCreateModal, P5 loses GalleryCreateModal). Commit `docs(plans): mark P2 done`.
- [ ] Step 6 (human): visual check at 390px / 1280px, light + dark: login, home, feed live arrival (post from a second browser), pill, widget reorder by keyboard, chat dock.
