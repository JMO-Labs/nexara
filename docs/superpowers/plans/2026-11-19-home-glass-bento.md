# Home Glass Bento Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the signed-in home (`/app`) with the glass bento design: cross-group feed, ranked chats with inline reply, upcoming events, photo mosaic, people strip, needs-you chips, gradient + pattern backdrop, new palette/font/logo, phone accordion.

**Architecture:** Backend adds three read endpoints under `/api/v1/home` (`chats`, `people`, `needs`), chat read-state (`chat_reads` + `POST /chat/channels/{id}/read`), and appearance fields. Frontend re-points the existing `--nx-*` tokens to the new palette app-wide, adds glass utilities, swaps the desktop side rail for a top pill nav, and rebuilds `app/app/page.tsx` from small tile components that render as glass panels on desktop and as an accordion on phone.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest · Next.js 16, React 19, Tailwind v4, TanStack Query, zustand, framer-motion 12, vitest.

**Spec:** `docs/superpowers/specs/2026-11-19-home-glass-bento.md` (mockup: `docs/superpowers/specs/2026-11-19-home-glass-bento-mockup.html`). Executors read both.

## Global Constraints

- Layering: `api/v1` → `services` → `repositories` → `models`. Routes never import repos.
- Every repo query filters `community_id`; viewer-scoped reads call `apply_block_filter`.
- Errors via `core/exceptions.py`; no raw `HTTPException` in services.
- Files ≤ 400 lines; Doxygen `@file`/`@brief` header on every new file, `@brief` on public functions.
- TDD: failing test first. Backend unit idiom: `AsyncMock(spec=Repo)`, `MagicMock(spec=User)`, `COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")`.
- Frontend tests: `renderWithProviders` from `tests/utils/renderWithProviders.tsx`; mock hooks/api with `vi.mock`; no MSW.
- Backend lint: `ruff check . && ruff format --check . && mypy app/`. Frontend: `npx tsc --noEmit && npx eslint . && npx prettier --check .`.
- Migration `down_revision = "0030_list_notif_email_defaults"`; `tests/unit/migrations/test_single_head.py` must pass.
- Pattern names, exactly: `none | dots | topo | contour | waves | grain`. Default `contour`.
- Group fallback palette, exactly: `["#83A2DB", "#D0965E", "#45A29C", "#A485C8", "#CE6969", "#7FA35B"]`.
- Copy: sentence case, no trailing arrows, no ALL CAPS labels. Wordmark: "nex" weight 600 + "ara" weight 300.
- WCAG 2.1 AA: palette contrast test stays green; every icon-only control has `aria-label`.
- Motion: framer-motion only; honour `useReducedMotion()`; hover effects only under `(hover: hover)`.
- Agents do **not** commit; the orchestrator commits per wave with Conventional Commits.

## Review Focus

1. **User in zero groups / brand-new community** → every tile shows a designed empty state with one action; scope bar shows only "Everything"; no crash on empty arrays. (Tests in Tasks 9–12.)
2. **Privacy flags** → `show_online_status=false` hides online dot, `show_last_seen=false` nulls `last_seen_at`, `show_birthday_to != "community"` hides birthday; blocked users never appear in people. (Task 4.)
3. **Chat thread with no read row** → unread counts only the last 7 days, not the channel's whole history; own messages never count as unread. (Task 2.)
4. **Scope filter selects a group with no items in a tile** → that tile shows "Nothing from {group} yet", not a blank panel. (Task 9.)
5. **Reduce transparency / reduced motion** → glass becomes solid and no entrance/sheen animation runs; content fully visible at rest. (Tasks 6, 15.)

---

## Contracts (shared by backend and frontend tasks)

```text
GET  /api/v1/home/chats?limit=4 (1..20)  -> HomeChatsResponse { items: HomeChatThread[] }
HomeChatThread { channel_id: uuid, name: str, channel_type: "community"|"subgroup"|"direct",
  subgroup_id: uuid|null, peer: {id, display_name, avatar_url}|null,
  last_message: {id, author_name: str|null, content: str (<=140 chars), created_at}|null,
  unread_count: int, mentions_me: bool, last_activity_at: datetime }
POST /api/v1/chat/channels/{channel_id}/read -> 204 (404 when viewer lacks access)

GET  /api/v1/home/people?limit=10 (1..20) -> HomePeopleResponse { items: HomePerson[] }
HomePerson { user_id, username, display_name, avatar_url, online: bool,
  birthday_in_days: int|null (0..7), last_seen_at: datetime|null,
  shared_groups: {id, name, accent_color: str|null}[], primary_group_id: uuid|null,
  shared_events_30d: int }

GET  /api/v1/home/needs -> HomeNeedsResponse {
  rsvps: {event_id, title, starts_at}[], polls: {post_id, question}[],
  prompt: {prompt_post_id, post_id, title}|null,
  list_items: {count, list_id, list_title}|null }

user_settings: + home_pattern: str|null (null = community default), + reduce_transparency: bool (false)
community_branding: + home_pattern: str (default "contour")
```

---

## Wave 1 (parallel): Tasks 1, 5, 6

### Task 1: Backend foundation — migration, settings fields, route stubs

**Files:**
- Create: `backend/alembic/versions/0032_home_glass_bento.py`, `backend/app/models/chat_read.py`, `backend/app/api/v1/home_chats.py`, `backend/app/api/v1/home_people.py`, `backend/app/api/v1/home_needs.py`
- Modify: `backend/app/models/user_settings.py`, `backend/app/models/branding.py`, `backend/app/models/__init__.py`, `backend/app/schemas/settings.py`, branding schemas (`backend/app/schemas/branding.py`), `backend/app/api/v1/home.py` (include the 3 new routers next to the feed/activity includes at :33-34)
- Test: `backend/tests/unit/migrations/test_home_glass_migration.py`, `backend/tests/unit/api/test_settings_appearance.py`

**Interfaces:**
- Produces: `ChatRead` model (table `chat_reads`: `user_id` FK users CASCADE, `channel_id` FK chat_channels CASCADE, composite PK, `community_id`, `last_read_at` timestamptz not null); `UserSettings.home_pattern: str | None`, `UserSettings.reduce_transparency: bool`; `CommunityBranding.home_pattern: str`; three empty `router = APIRouter()` modules registered under `/home`.

- [ ] **Step 1: Write failing tests**
```python
def test_migration_parent_and_head():  # parse file
    assert mod.down_revision == "0030_list_notif_email_defaults"
    assert mod.revision == "0032_home_glass_bento"

async def test_settings_accepts_pattern_and_transparency(client):  # PUT /api/v1/settings/
    r = await client.put("/api/v1/settings/", json={"home_pattern": "waves", "reduce_transparency": True})
    assert r.status_code == 200 and r.json()["home_pattern"] == "waves"

async def test_settings_rejects_unknown_pattern(client):
    r = await client.put("/api/v1/settings/", json={"home_pattern": "plaid"}); assert r.status_code == 422
```
- [ ] **Step 2: Run** `pytest tests/unit/migrations/test_home_glass_migration.py tests/unit/api/test_settings_appearance.py -v` → FAIL.
- [ ] **Step 3: Implement** model, migration (create `chat_reads` + index `(user_id)`; add the 3 columns; `reduce_transparency` server_default `false`, branding `home_pattern` server_default `'contour'`), schema fields with pattern regex `^(none|dots|topo|contour|waves|grain)$` (settings field nullable), stub routers.
- [ ] **Step 4: Run** the two test files + `tests/unit/migrations/test_single_head.py` → PASS; `ruff check . && mypy app/` clean.

### Task 5: Design tokens, font, glass utilities

**Files:**
- Modify: `frontend/app/globals.css`, `frontend/theme/palette.ts`, `frontend/theme/font.ts`, `frontend/app/layout.tsx` (font variable, viewport `themeColor` light `#E4E4E4` / dark `#0D1117`)
- Test: `frontend/tests/unit/theme/palette.test.ts`, Create `frontend/tests/unit/theme/glass.test.ts`

**Interfaces:**
- Produces CSS tokens (light / dark), declared in `:root`, `.dark`, `@theme inline`, and `palette.ts`:

| token | light | dark |
|---|---|---|
| `--nx-bg` | `#E4E4E4` | `#0D1117` |
| `--nx-surface` | `#F5F6F9` | `#1A202A` |
| `--nx-surface-strong` | `#10141A` | `#E9ECF2` |
| `--nx-ink` | `#10141A` | `#E9ECF2` |
| `--nx-accent` | `#3B5E9E` | `#A9C1EE` |
| `--nx-sun` | `#E9C27A` | `#E4BC72` |
| `--nx-leaf` | `#45A29C` | `#5BB8B1` |
| `--nx-muted` / `--nx-nav-muted` | `#4C5361` | `#A9B0BD` |
| `--nx-danger` | `#B54848` | `#DB7B7B` |
| `--nx-danger-fg` | `#FFFFFF` | `#10141A` |
| new `--nx-blue` | `#83A2DB` | `#8FAEE6` |
| new `--nx-red` | `#CE6969` | `#DB7B7B` |
| new `--nx-ok` | `#3E9E68` | `#5CC08A` |
| new `--nx-glass` | `rgba(255,255,255,.44)` | `rgba(22,28,40,.52)` |
| new `--nx-glass-edge` | `rgba(255,255,255,.72)` | `rgba(255,255,255,.09)` |
| new `--nx-glass-hi` | `rgba(255,255,255,.9)` | `rgba(255,255,255,.12)` |
| new `--nx-glass-solid` | `#F1F3F6` | `#1A202A` |
| new `--nx-item` | `rgba(255,255,255,.58)` | `rgba(255,255,255,.06)` |
| new `--nx-item-edge` | `rgba(255,255,255,.85)` | `rgba(255,255,255,.07)` |
| new `--nx-sheen` | `rgba(255,255,255,.55)` | `rgba(255,255,255,.09)` |
| new `--nx-pattern` | `rgba(16,20,26,.09)` | `rgba(233,236,242,.07)` |
| new `--nx-bubble` | `#E6E9EF` | `rgba(255,255,255,.08)` |

  Utility classes in `globals.css` (`@layer components`): `.glass` (fill `--nx-glass`, 1px `--nx-glass-edge`, `box-shadow: inset 0 1px 0 var(--nx-glass-hi)`, `backdrop-filter: blur(26px) saturate(1.6)`), `.glass-sheen` (`::after` radial gradient at `var(--mx) var(--my)` using `--nx-sheen`, opacity 0 → 1 on hover under `@media (hover:hover) and (prefers-reduced-motion:no-preference)`), `.sweep` (diagonal light sweep on hover, same media guard), `.glass-item` (fill `--nx-item`, edge `--nx-item-edge`). `.glass-btn` (ref: framer.com/marketplace/components/glassy-button — frosted fill `--nx-glass`, 1px `--nx-glass-edge`, `inset 0 1px 0 var(--nx-glass-hi)` top shine + `inset 0 -1px 0 rgba(0,0,0,.06)` bottom, soft drop shadow `0 6px 16px -8px rgba(16,20,26,.35)`, `backdrop-filter: blur(20px)`; hover: `translateY(-1px)` + brighter shine; active: `scale(.97)` + deeper inset; transitions 150ms, none under reduced motion). Add `variant: "glass"` to `components/ui/Button.tsx` mapping to `.glass-btn`; icon buttons in TopBar/tiles use it. Solid fallback: `[data-transparency="reduced"] .glass` and `@media (prefers-reduced-transparency: reduce)` → background `--nx-glass-solid`, no backdrop-filter, `.glass-sheen::after{display:none}`.
- Font: `theme/font.ts` exports `outfit` (next/font/google `Outfit`, weights 300/400/500/600, variable `--font-outfit`); `--font-sans: var(--font-outfit), system-ui, sans-serif`. Remove `hanken`.

- [ ] **Step 1: Failing tests** — update `palette.test.ts` expectations to new values; add in the `test.each`:
```ts
expect(contrastRatio(p.ink, p["glass-solid"])).toBeGreaterThanOrEqual(4.5);
expect(contrastRatio(p.muted, p["glass-solid"])).toBeGreaterThanOrEqual(4.5);
expect(contrastRatio(p.accent, p.surface)).toBeGreaterThanOrEqual(4.5);
expect(contrastRatio(p["danger-fg"], p.danger)).toBeGreaterThanOrEqual(4.5);
```
  `glass.test.ts`: read `app/globals.css` as text; assert it contains `.glass`, `backdrop-filter`, `prefers-reduced-transparency`, `[data-transparency="reduced"]`.
- [ ] **Step 2: Run** `npx vitest run tests/unit/theme` → FAIL.
- [ ] **Step 3: Implement** tokens/utilities/font. If an existing palette assertion fails with the table values, adjust the failing token's value minimally (keep hue) and note it in the report.
- [ ] **Step 4: Run** `npx vitest run tests/unit/theme && npx tsc --noEmit` → PASS.

### Task 6: Brand components and icons

**Files:**
- Create: `frontend/components/brand/Logo.tsx`, `frontend/public/icons/icon-192.png`, `icon-512.png`, `apple-touch-icon.png` (copy from `public/brand/nexara-color-tile-192.png`, `-512.png`, `-180.png`)
- Modify: `frontend/app/favicon.ico` (replace with `/home/user/code/nexara/design/brand/favicon.ico`), `frontend/public/manifest.webmanifest` (`theme_color "#10141A"`, `background_color "#E4E4E4"`, icon paths unchanged), `frontend/app/globals.css` only to add logo vars `--nx-logo-1/2/3`, `--nx-logo-fo`, `--nx-logo-blend` (light `#E9C27A #CE6969 #83A2DB .8 multiply`; dark `#E4BC72 #DB7B7B #8FAEE6 .72 normal`) — append in a separate block at end of file to avoid conflict with Task 5.
- Test: `frontend/tests/unit/brand/Logo.test.tsx`

**Interfaces:**
- Produces: `LogoMark({ size = 32, className }: {size?: number; className?: string})` — inline SVG, viewBox `0 0 512 512`, geometry copied from `public/brand/nexara-light.svg`, circle fills `var(--nx-logo-1..3)`, strokes `currentColor`, `aria-hidden`. `Wordmark({ className })` → `<span>nex<span className="font-light">ara</span></span>` with outer `font-semibold`. `BrandLockup({ logoUrl, name, size })` → custom `<img>` when `logoUrl` set, else `LogoMark` + `Wordmark`; accessible name = `name`.

- [ ] **Step 1: Failing tests**: `BrandLockup` without `logoUrl` renders an `svg` and text "nexara"; with `logoUrl` renders `img[alt="Maple"]`; `Wordmark` "ara" span has class `font-light`.
- [ ] **Step 2: Run** `npx vitest run tests/unit/brand` → FAIL. **Step 3: Implement.** **Step 4:** PASS.

---

## Wave 2 (parallel): Tasks 2–4, 7, 8

### Task 2: Chat read state + home chats endpoint

**Files:**
- Create: `backend/app/repositories/chat_read_repo.py`, `backend/app/schemas/home_chats.py`, `backend/app/services/home_chats_service.py`
- Modify: `backend/app/services/chat_service.py` (`send_message`: after `create_message`, `await self._read_repo.mark_read(user.id, channel_id)`; add `mark_read(user, channel_id)` service method using `get_for_user` access check → `NotFoundError`), `backend/app/api/v1/chat.py` (`POST /channels/{channel_id}/read`, 204), `backend/app/api/v1/home_chats.py` (`GET /chats`), DI wiring in `core/dependencies.py` if ChatService is built there.
- Test: `backend/tests/unit/services/test_home_chats_service.py`, `backend/tests/unit/api/test_home_chats_api.py`, `backend/tests/integration/repositories/test_chat_read_repo.py`

**Interfaces:**
- Consumes: `ChatRead` (Task 1); `ChatChannelRepository.list_for_user(user_id, community_id)`, `list_dm_threads`.
- Produces: `ChatReadRepository(session)`: `mark_read(user_id, channel_id, community_id, at: datetime | None = None) -> None` (upsert, never moves backwards); `channel_stats(user_id, username, channel_ids, community_id, since_default: datetime) -> dict[UUID, ChannelStat]` where `ChannelStat = (last_message: ChatMessage | None, last_author_name: str | None, unread_count: int, mentions_me: bool)`. `HomeChatsService(channel_repo, read_repo, community_id).list(user, limit) -> HomeChatsResponse`.

Rules: unread = messages with `author_id != user` and `created_at > coalesce(last_read_at, since_default)`, `since_default = now - 7 days`. `mentions_me` = any unread message matching `~* ('(^|\W)@' || username || '\M')`. Ranking key `(not mentions_me, unread_count == 0, -last_activity_at)`; `last_activity_at = last_message.created_at or channel.created_at`. `content` truncated to 140 chars with "…". DM `name` = peer display name.

- [ ] **Step 1: Failing tests** (service, mocked repos):
```python
async def test_ranks_mentions_then_unread_then_recent(): # 3 channels: recent/no-unread, older/unread, oldest/mention
    assert [t.name for t in resp.items] == ["mention", "unread", "recent"]
async def test_limit_applies_after_ranking(): assert len(resp.items) == 2
async def test_dm_uses_peer_name(): assert resp.items[0].name == "Leo Delgado" and resp.items[0].peer.id == peer.id
async def test_truncates_preview(): assert len(resp.items[0].last_message.content) <= 140
```
  Integration repo test (real Postgres): own messages not unread; no read row counts only last 7 days; `mark_read` with older `at` does not move backwards; `@ana` matches `Hi @Ana!` but not `@anabel`.
  API: `GET /api/v1/home/chats` 401 unauthenticated; 200 shape; `limit=99` → 422. `POST /api/v1/chat/channels/{id}/read` → 204; service raising `NotFoundError` → 404 envelope.
- [ ] **Step 2: Run** the three files → FAIL. **Step 3: Implement.** **Step 4:** PASS + `ruff`, `mypy`.

### Task 3: Home people endpoint

**Files:**
- Create: `backend/app/repositories/home_people_repo.py`, `backend/app/schemas/home_people.py`, `backend/app/services/home_people_service.py`; fill `backend/app/api/v1/home_people.py`
- Test: `backend/tests/unit/services/test_home_people_service.py`, `backend/tests/unit/api/test_home_people_api.py`, `backend/tests/integration/repositories/test_home_people_repo.py`

**Interfaces:**
- Produces: `HomePeopleRepository(session)`: `candidates(viewer_id, community_id, limit) -> list[PersonRow]` (users sharing a direct `SubgroupMember` subgroup with viewer, plus community members to fill up to `limit*3`; excludes viewer, bots, inactive; `apply_block_filter`), each row carries `user`, `settings` (`show_online_status`, `show_last_seen`, `show_birthday_to`), `shared_groups: list[(id, name, accent_color, member_count)]`; `shared_event_counts(viewer_id, user_ids, community_id, window_days=30) -> dict[UUID, int]` (events with `starts_at` in ±30 days where both have `status == "attending"`). `HomePeopleService(repo, community_id, online_fn=presence.get_online_users, today_fn=date.today).list(viewer, limit) -> HomePeopleResponse`.

Rules: `online` only if `show_online_status`; `last_seen_at` null if not `show_last_seen`; `birthday_in_days` (0..7, handles year wrap and Feb 29 → Feb 28 in non-leap years) only if `show_birthday_to == "community"`; `primary_group_id` = shared group with the smallest `member_count` (tie → name); order: online, then `birthday_in_days` asc, then `last_seen_at` desc nulls last; then `limit`.

- [ ] **Step 1: Failing tests:**
```python
async def test_orders_online_then_birthday_then_recent(): assert [p.display_name for p in r.items] == ["Ruth", "Leo", "Kim"]
async def test_hides_online_when_flag_off(): assert r.items[0].online is False
async def test_hides_birthday_unless_community(): assert r.items[0].birthday_in_days is None
async def test_birthday_wraps_year(): # today Dec 30, birthday Jan 2
    assert r.items[0].birthday_in_days == 3
async def test_primary_group_is_smallest_shared(): assert r.items[0].primary_group_id == small.id
```
  Integration: blocked user excluded; viewer excluded; shared event count = 1 for one mutual attending event.
  API: 401; 200 shape; `limit=99` → 422.
- [ ] **Steps 2–4:** run → FAIL, implement, PASS + lint.

### Task 4: Home needs endpoint

**Files:**
- Create: `backend/app/repositories/home_needs_repo.py`, `backend/app/schemas/home_needs.py`, `backend/app/services/home_needs_service.py`; fill `backend/app/api/v1/home_needs.py`
- Test: `backend/tests/unit/services/test_home_needs_service.py`, `backend/tests/unit/api/test_home_needs_api.py`, `backend/tests/integration/repositories/test_home_needs_repo.py`

**Interfaces:**
- Produces: `HomeNeedsRepository(session)`: `pending_rsvps(viewer_id, community_id, subgroup_ids, now, days=14, limit=5)`; `open_polls(viewer_id, community_id, subgroup_ids, now, limit=5)`; `unanswered_prompt(viewer_id, community_id, now)`; `due_list_items(viewer_id, community_id, subgroup_ids, now, days=7) -> tuple[int, UUID | None, str | None]`. `HomeNeedsService(repo, member_repo: SubgroupMemberRepository, community_id).get(viewer) -> HomeNeedsResponse` (subgroup_ids = keys of `list_my_roles(viewer.id)`).

Rules: rsvps — events visible to viewer (community, or subgroup in subgroup_ids), `starts_at` in [now, now+14d], not authored by viewer, no `EventAttendance` row for viewer; asc by `starts_at`. polls — post created ≥ now−7d, poll not closed, `expires_at` null or > now, not authored by viewer, no `PollVote` by viewer, post visible (community or subgroup in subgroup_ids); newest first. prompt — newest active `PromptPost` (`is_finalised` false, `expires_at > now`) with no `Post` where `reply_to_prompt_id = prompt_post.id` and `author_id = viewer`; `title` = the prompt's question text. list_items — `ListItem` with `completed` false, `deleted_at` null, `due_at` in [now, now+7d], in `List.status == "active"` visible to viewer (`ListRepository.can_view` semantics); return count and the list of the soonest item; `null` when count 0.

- [ ] **Step 1: Failing tests** (service with mocked repo): empty repo results → `rsvps == [] and polls == [] and prompt is None and list_items is None`; passes `subgroup_ids` from `list_my_roles`. Integration (real Postgres): event with viewer's attendance excluded; event authored by viewer excluded; event 15 days out excluded; voted poll excluded; expired poll excluded; prompt answered by viewer excluded; completed list item excluded. API: 401; 200 shape.
- [ ] **Steps 2–4:** run → FAIL, implement, PASS + lint.

### Task 7: App shell — top pill nav, backdrop, patterns, tab bar

**Files:**
- Create: `frontend/lib/patterns.ts`, `frontend/components/layout/AppBackdrop.tsx`, `frontend/components/layout/TopNav.tsx`, `frontend/components/layout/CreateMenu.tsx`
- Modify: `frontend/components/layout/Shell.tsx` (remove `<SideNav/>` and `md:pl-16`; render `<AppBackdrop/>` first; root gets `data-transparency={reduced ? "reduced" : undefined}` from `useUserSettings().data?.reduce_transparency`; root bg becomes transparent so backdrop shows), `TopBar.tsx` (desktop: `BrandLockup` · `TopNav` · `CreateMenu` · search · bell · `AvatarMenu`; phone: `BrandLockup` · `CreateMenu` (icon-only) · bell · avatar button opening `MoreSheet`), `BottomTabBar.tsx` (items: Home `/app`, Chat `/app/chat` with unread badge from `useChatRealtime().unread` sum, center Create, Calendar `/app/events`, Photos `/app/galleries`; glass, pinned bottom, safe-area padding), `navItems.tsx` (add `TOP_NAV`: Home `/app`, Chat `/app/chat`, Calendar `/app/events`, Photos `/app/galleries`, Groups `/app/subgroups`; `More` dropdown = `MORE_NAV`)
- Delete: `frontend/components/layout/SideNav.tsx`, `frontend/tests/unit/layout/SideNav.test.tsx`
- Test: `frontend/tests/unit/layout/{TopNav,AppBackdrop,CreateMenu}.test.tsx`, `frontend/tests/unit/lib/patterns.test.ts`; update `Shell.test.tsx`, `TopBar.test.tsx`, `BottomTabBar.test.tsx`, `tests/e2e/mobile-nav.spec.ts`

**Interfaces:**
- Consumes: `.glass`, tokens (Task 5); `BrandLockup` (Task 6); `HomePattern` type and settings fields (Task 8 adds them to `lib/api/settings.ts` — until then type locally as `type HomePattern = "none"|"dots"|"topo"|"contour"|"waves"|"grain"` exported from `lib/patterns.ts`; Task 8 imports it from there).
- Produces: `lib/patterns.ts`: `export const PATTERNS: readonly HomePattern[]`; `patternUrl(p: HomePattern): string | null` (CSS `url("data:image/svg+xml,…")`; `null` for `none`; port generators from the mockup — `contour()` dot field + `topo()` rings, dots/waves/grain SVG strings). `AppBackdrop()` — fixed, `inset-0`, `-z-10`, `aria-hidden`; gradient layer (`radial-gradient` blobs of `--nx-blue` top-left and `--nx-red` bottom-right over `--nx-bg`, `filter: blur(46px)`) + pattern layer (`background: var(--nx-pattern)`, `mask: <patternUrl> repeat`). Pattern = `settings.home_pattern ?? branding.home_pattern ?? "contour"`. `TopNav` "dynamic island" behavior (ref: framer.com/marketplace/components/dynamic-island-nav): the active pill is a `motion.span` with `layoutId="topnav-pill"` (spring `stiffness 500, damping 40`) that glides between items; after scrolling down > 80px the nav compacts to logo + active item only (width animates via `layout`); scrolling up restores it. `useScrollDirection(threshold = 80): "up" | "down"` helper in `frontend/hooks/useScrollDirection.ts`. Reduced motion → no glide, no compaction. Phone `BottomTabBar` gets the same gliding pill (`layoutId="tabbar-pill"`) but never hides (spec: pinned). `CreateMenu({ compact }: {compact?: boolean})` — DropdownMenu with "New post", "New event", "Upload photos", "New list"; reuse the actions/routes from `components/home/widgets/QuickActionsWidget.tsx`.

- [ ] **Step 1: Failing tests:** `patternUrl("none") === null`; every other pattern returns a string starting `url("data:image/svg+xml,`; `contour` output deterministic (same string twice). `TopNav` marks `/app/events` link `aria-current="page"` when pathname `/app/events`. `AppBackdrop` uses `waves` when settings say waves, `contour` when settings and branding are null. `CreateMenu` opens and lists the four items. `TopNav` adds `data-compact="true"` after a scroll-down event past 80px and removes it on scroll-up (mock `useScrollDirection`); with reduced motion it never compacts. `BottomTabBar` shows Chat badge "3" when unread sums to 3, and has 5 items. Shell no longer renders a `nav` with `aria-label="Primary"` side rail.
- [ ] **Steps 2–4:** run `npx vitest run tests/unit/layout tests/unit/lib/patterns.test.ts` → FAIL, implement, PASS; `npx tsc --noEmit`.

### Task 8: Frontend API clients, hooks, query keys, group colors

**Files:**
- Modify: `frontend/lib/api/home.ts` (types + `getHomeChats(limit=4)`, `getHomePeople(limit=10)`, `getHomeNeeds()`), `frontend/lib/api/chat.ts` (`markChannelRead(channelId): Promise<void>` → `POST /api/v1/chat/channels/{id}/read`), `frontend/lib/api/settings.ts` (`home_pattern: HomePattern | null`, `reduce_transparency: boolean` on `UserSettings` and `UserSettingsUpdate`; import `HomePattern` from `lib/patterns.ts`), `frontend/lib/api/branding.ts` (`home_pattern: HomePattern`), `frontend/lib/query-keys.ts` (`qk.home.chats()`, `qk.home.people()`, `qk.home.needs()`)
- Create: `frontend/hooks/useHomeChats.ts`, `frontend/hooks/useHomePeople.ts`, `frontend/hooks/useHomeNeeds.ts`, `frontend/lib/groupColor.ts`
- Test: `frontend/tests/unit/hooks/{useHomeChats,useHomePeople,useHomeNeeds}.test.tsx`, `frontend/tests/unit/lib/groupColor.test.ts`

**Interfaces:**
- Consumes: Contracts section; `HomePattern` from `lib/patterns.ts` (Task 7 — if absent when you start, create `lib/patterns.ts` exporting only the type and `PATTERNS`; Task 7 extends it).
- Produces: TS types `HomeChatThread`, `HomeChatsResponse`, `HomePerson`, `HomePeopleResponse`, `HomeNeeds` (names mirror contracts, snake_case fields). Hooks: `useHomeChats(limit = 4)` (staleTime 30s; invalidates itself on `chat.message` frames via `useChatRealtime` — subscribe through the existing realtime hook, don't open a second socket); `useHomePeople()` (staleTime 60s); `useHomeNeeds()` (staleTime 60s). `groupColor(subgroupId: string | null, accent?: string | null): string` — `accent` if set; `null` id → `"var(--nx-blue)"`; else fallback palette index = (sum of char codes of id) mod 6.

- [ ] **Step 1: Failing tests:** each hook calls its API fn once and returns data (mock `@/lib/api/home`); `groupColor(null) === "var(--nx-blue)"`; `groupColor("abc", "#123456") === "#123456"`; same id → same color; result ∈ palette.
- [ ] **Steps 2–4:** run → FAIL, implement, PASS; `npx tsc --noEmit`.

---

## Wave 3: Task 9

### Task 9: Home page frame — layout, tile shell, scope, accordion

**Files:**
- Create: `frontend/components/home/HomeTile.tsx`, `frontend/components/home/Greeting.tsx`, `frontend/components/home/ScopeBar.tsx`, `frontend/stores/homeScope.ts`, `frontend/hooks/useHomeAccordion.ts`
- Modify: `frontend/app/app/page.tsx` (no nested `<main>`; use `<div>`), `frontend/components/home/HomeFeed.tsx` only if needed to accept `scope` (prefer filtering in Task 10's FeedTile)
- Delete: `WidgetColumn.tsx`, `widgetRegistry.tsx`, `WidgetFrame.tsx`, `WelcomeBanner.tsx`, `NextUpCard.tsx`, `components/home/widgets/*`, `hooks/useHomeLayout.ts` and their tests (keep `dayPart` by moving it into `Greeting.tsx`)
- Test: `frontend/tests/unit/home/{HomeTile,ScopeBar,Greeting}.test.tsx`, `frontend/tests/unit/hooks/useHomeAccordion.test.ts`, rewrite `frontend/tests/unit/app/home-page.test.tsx`

**Interfaces:**
- Consumes: `.glass`, `.glass-sheen` (Task 5); `useSubgroupList()`; `groupColor` (Task 8).
- Produces:
  - `useHomeScope` zustand store: `{ scope: string | "all"; setScope(s) }` (not persisted).
  - `inScope(subgroupId: string | null, scope: string): boolean` exported from `stores/homeScope.ts` (`"all"` → true; else `subgroupId === scope`).
  - `useHomeAccordion(defaultOpen: TileId | null)` → `{ open: TileId | null; toggle(id: TileId): void }`, `type TileId = "next" | "chat" | "photos" | "feed"`.
  - `HomeTile({ id, title, icon: LucideIcon, href, linkLabel, summary, count, hot, open, onToggle, children, className })`: desktop (`md:`) = `section.glass.glass-sheen rounded-[32px]` with header `h2` + link; phone = header is a `button` with `aria-expanded`, `aria-controls`, summary line, count badge (`bg-[var(--nx-red)]` if `hot` else `bg-[var(--nx-blue)]`, `aria-label` "{count} need you"/"{count} new"), chevron; body hidden when `!open` (phone only; always shown at md+ via CSS `md:block`). Pointer sheen: on `pointermove` set `--mx`/`--my` percent style vars.
  - `Greeting({ name })`: h1 "Good {morning|afternoon|evening}, {first}" + date line `Thursday, November 19` (`Intl.DateTimeFormat` weekday/long month/day).
  - `ScopeBar({ needs }: { needs: React.ReactNode })`: left glass group (Everything + member groups, each with color dot; `aria-pressed`), right glass group = `needs` slot, `overflow-x-auto`, no wrap, phone stacks the two groups.
  - Page layout: `Greeting` + people slot (right) → `ScopeBar` → desktop grid `grid-cols-[1.3fr_1fr_.8fr] grid-rows-[1fr_auto]` areas `feed chat next / feed chat photos`, height `800px`; phone flex column order next, chat, photos, feed. Default open (phone): `"chat"` if any chat thread `mentions_me`, else `"next"`. Slots for tiles from Tasks 10–13 are imported by name: `FeedTile`, `ChatsTile`, `UpNextTile`, `PhotosTile`, `PeopleStrip`, `NeedsChips` — create each as a stub returning `null` with a TODO-free `@brief` so the page compiles; the owning task replaces it.

- [ ] **Step 1: Failing tests:** `Greeting` at 19:00 renders "Good evening, Ana"; `ScopeBar` click on "Book club" sets store scope to its id and marks it `aria-pressed="true"`; `inScope(null, "x") === false`, `inScope("x","all") === true`; `useHomeAccordion("chat")` toggling "chat" → `null`, toggling "next" → `"next"`; `HomeTile` (phone) collapsed hides children and shows summary + count, button `aria-expanded="false"`; home page renders the six slots.
- [ ] **Steps 2–4:** run → FAIL, implement, PASS; `npx tsc --noEmit && npx eslint components/home app/app`.

---

## Wave 4 (parallel): Tasks 10–14

### Task 10: FeedTile
**Files:** Create `frontend/components/home/tiles/FeedTile.tsx`; modify `HomeFeed.tsx` to accept `{ filter?: (item: FeedItem) => boolean; embedded?: boolean }` (embedded = scrolls inside the tile, sentinel observes the tile's scroll container, `NewItemsPill` positioned inside tile). Test `frontend/tests/unit/home/tiles/FeedTile.test.tsx`.
**Interfaces:** Consumes `HomeTile`, `useHomeScope`, `inScope`. Post group = `item.post.subgroup_id`; activity items pass only when scope is `"all"`. Summary (phone): "{n} new posts" from `useHomeSummary().data.new_posts`, `count` = `new_posts`, `hot` false.
- [ ] Tests: with scope = group A, a post from group B is not rendered; empty after filter shows "Nothing from {group name} yet"; summary count equals `new_posts`. Run → FAIL, implement, PASS.

### Task 11: ChatsTile with inline reply
**Files:** Create `frontend/components/home/tiles/ChatsTile.tsx`, `frontend/components/home/tiles/ChatThreadRow.tsx`, `frontend/components/home/tiles/InlineThread.tsx`. Test `frontend/tests/unit/home/tiles/ChatsTile.test.tsx`.
**Interfaces:** Consumes `useHomeChats(4)`, `useMessages(channelId, 3)`, `sendChatMessage`, `optimisticAddMessage`, `markChannelRead`, `groupColor`, `inScope` (direct threads pass only for scope `"all"`). One thread open (default first item). `ChatThreadRow({ thread, open, onOpen })`: group dot + name, preview, badge (`@` red if `mentions_me`, else unread number blue, else time). `InlineThread({ thread })`: last 3 messages (bubble `--nx-bubble`, own messages ink pill, newest at bottom), reply form (`input` with `aria-label="Reply to {name}"`, send button `aria-label="Send"`); submit → `optimisticAddMessage` + `sendChatMessage` + `markChannelRead` + invalidate `qk.home.chats()`; opening a thread calls `markChannelRead`. framer-motion `layout` on rows and `AnimatePresence` for messages. Phone: summary = top thread's `last_message` "{author}: {content}", `count` = sum unread, `hot` = any `mentions_me`. Footer link "See all chats" → `/app/chat`.
- [ ] Tests: renders threads in API order; clicking second row opens it and collapses first (`aria-expanded`); submitting "On my way" calls `sendChatMessage(channelId, "On my way")` and `markChannelRead(channelId)`, clears input; empty reply does nothing; zero threads → empty state "No chats yet" with link "Start a chat". Run → FAIL, implement, PASS.

### Task 12: UpNextTile and PhotosTile
**Files:** Create `frontend/components/home/tiles/UpNextTile.tsx`, `frontend/components/home/tiles/PhotosTile.tsx`, `frontend/lib/mediaUrl.ts`. Tests `frontend/tests/unit/home/tiles/{UpNextTile,PhotosTile}.test.tsx`, `frontend/tests/unit/lib/mediaUrl.test.ts`.
**Interfaces:** `mediaThumbUrl(m: { id: string; thumbnail_key: string | null }): string` → `${API_BASE}/api/v1/media/${id}/thumbnail` when `thumbnail_key` else `/file`. UpNext: `useUpcomingEvents(30)` filtered by `inScope(e.subgroup_id)`, first 3; row = date block (weekday short + day number), title, "{time}, {location}"; trailing ✓ (`aria-label="Going"`, `--nx-ok`) when `user_rsvp?.status === "attending"`, else `RSVP` button (`.sweep`) calling `useRsvp(id).mutate("attending")`. Phone summary: first event "{title}, {weekday}"; `count` = events without RSVP in list; `hot` = count > 0. Photos: `useHomeMedia({ limit: 7 })`; title = first item's `source_title ?? "Recent photos"`; grid `grid-cols-3`, first tile `col-span-2 row-span-2`, others `aspect-square`; `img` `object-cover w-full h-full`, `alt` = `alt_text ?? ""`; 7th tile shows "+{remaining}" overlay when more exist (use `next_cursor` presence → "+"; exact count not required); no `.sweep` on photos. Phone summary "{n} new photos", `count` = n, `hot` false. Empty: "No photos yet" + "Upload photos" link.
- [ ] Tests: attending event shows "Going" label, other shows RSVP button which calls mutate("attending"); scope filter hides other-group events; photos render 7 imgs max with `object-cover`; `mediaThumbUrl` picks thumbnail vs file. Run → FAIL, implement, PASS.

### Task 13: PeopleStrip and NeedsChips
**Files:** Create `frontend/components/home/PeopleStrip.tsx`, `frontend/components/home/ConnectionCard.tsx`, `frontend/components/home/NeedsChips.tsx`. Tests `frontend/tests/unit/home/{PeopleStrip,NeedsChips}.test.tsx`.
**Interfaces:** PeopleStrip: `useHomePeople()`; glass pill row, each avatar a `button` (`aria-label` "{name}, {status}" where status ∈ "Online now" / "Birthday in {n} days"/"Birthday today" / "Active {relative}" / "") with ring `groupColor(primary_group_id, accent)`, online dot `--nx-ok`, cake badge (lucide `Cake`) when `birthday_in_days != null`. Hover/focus shows `ConnectionCard` (desktop only): name, dashed inert chip "Add how you know {first}", shared group names, "{n} shared events this month" (omit when 0), status, buttons "Message" (`useCreateDm` then route `/app/chat?c={id}`) and "Profile" (`/app/members/{user_id}`). Phone: horizontal scroll, no card; tap → profile. Hidden when 0 people. NeedsChips: `useHomeNeeds()`; label "Needs you" with lucide `Inbox`; chips: one per rsvp "RSVP to {title}" (lucide `CalendarCheck`, red icon) → `/app/events?e={event_id}`; polls "Vote: {question}" (`BarChart3`) → `/app/post/{post_id}`; prompt "Today's prompt" (`Sparkles`) → `/app/post/{post_id}`; list items "{count} list items due" (`ListChecks`, red) → `/app/lists/{list_id}`. Renders nothing when all empty. Truncate chip text at 28 chars with "…".
- [ ] Tests: person with `online` shows status "Online now" in aria-label; birthday 0 → "Birthday today"; NeedsChips renders 4 chip kinds from fixture and nothing for empty needs; chip text truncation. Run → FAIL, implement, PASS.

### Task 14: Appearance settings + admin default pattern
**Files:** Modify `frontend/components/settings/AppearanceTab.tsx` (add "Background pattern" radio-card group with live swatch per pattern using `patternUrl`, option "Community default" = `null`; add "Reduce transparency" `Switch` with description "Makes panels solid. Easier to read on busy backgrounds."), admin branding form (find the branding settings tab under `components/admin/`; add "Default home pattern" select). If AppearanceTab exceeds 400 lines, extract `components/settings/PatternPicker.tsx`. Tests `frontend/tests/unit/settings/AppearanceTab.test.tsx` (extend), `frontend/tests/unit/settings/PatternPicker.test.tsx`.
- [ ] Tests: choosing "Waves" calls `useUpdateSettings().mutate({ home_pattern: "waves" })`; "Community default" sends `null`; toggling switch sends `{ reduce_transparency: true }`; admin select sends `home_pattern` in branding update. Run → FAIL, implement, PASS.

---

## Wave 5: Tasks 15–16

### Task 15: Motion pass
**Files:** Modify `frontend/app/app/page.tsx`, `HomeTile.tsx`; add variants `homeStagger`, `homeTile` to `frontend/components/ui/motion.ts`. Test `frontend/tests/unit/motion/home-motion.test.tsx`.
**Interfaces:** Entrance: page container `motion.div` with `homeStagger` (staggerChildren .07), children `homeTile` (`opacity 0→1, y 14→0`, duration .5) — only on first mount per session (module-level flag). Phone accordion open: body `motion.div` height auto animation via `AnimatePresence` + `collapseTransition`. Tile → page: tile header link wraps `motion.div` with `layoutId={"tile-"+id}`; on click, animate tile scale to 1.02 + fade (150ms) then `router.push(href)`. All return static elements when `useReducedMotion()` is true.
- [ ] Tests (mock `useReducedMotion`): reduced → no element has inline `opacity: 0` after mount; not reduced → container receives `variants` prop. Run → FAIL, implement, PASS.

### Task 16: Integration verification and cleanup (orchestrator)
- [ ] Remove dead imports/tests referencing deleted widgets; `grep -r "WidgetColumn\|useHomeLayout\|SideNav" frontend/` returns nothing (except git history).
- [ ] Update `tests/e2e/mobile-nav.spec.ts` for the new tab bar; add `tests/e2e/home.spec.ts` smoke (desktop: four tiles visible; phone: Chats expanded, tap "Up next" collapses Chats).
- [ ] Run full suites: backend `pytest -q && ruff check . && ruff format --check . && mypy app/`; frontend `npx vitest run && npx tsc --noEmit && npx eslint . && npx prettier --check . && npm run build`.
- [ ] Build the production image from the worktree (with the deploy fixes) and smoke `/healthz`, `/app` for user evaluation.

## Decisions taken in this plan (flag on review)
- New palette and Outfit font apply **app-wide** by re-pointing `--nx-*` tokens (cheapest path; other pages restyle automatically).
- Desktop side rail removed (spec: top pill nav only). No separate "Feed" nav item: the feed lives on Home and no standalone feed route exists.
- Group color = `subgroups.accent_color`, fallback palette (no new column).
- Polls render through existing `PostCard` (no poll UI exists today; poll rendering is out of scope).
