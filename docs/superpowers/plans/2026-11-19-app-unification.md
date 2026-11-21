# App Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Every signed-in page matches the glass system from Home; consolidate overlapping features; app works end to end in the production container.

**Architecture:** Fix the theme at its source (branding defaults), add shared page primitives in `frontend/components/ui/page/`, then migrate each section onto them in parallel, deleting dead/duplicate components as we go. Finish with Playwright e2e against the container and a screenshot polish pass per section.

**Spec:** `docs/superpowers/specs/2026-11-19-app-unification.md` (+ Home spec/mockup for visuals). Inventory facts come from the 2026-11-19 page inventory (summarised inline per task).

## Global Constraints
- All Phase 1 constraints apply (layering, ≤400 lines, Doxygen headers, TDD, AA, reduced motion, agents never touch git).
- No `PageMasthead`, no `font-mono uppercase` labels, no `bg-blue-*`/`purple-*`/lilac literals, no `bg-accent` as a selected-state fill (selected = ink pill `bg-surface-strong text-bg`).
- Page content lives inside Shell's frame (`max-w-[1440px] mx-auto`); pages do not add their own outer max-width/padding wrappers (narrow reading columns like post detail may use `max-w-3xl mx-auto`).
- Use primitives from `components/ui/page/` instead of re-implementing search fields, segmented pills, panels, side-nav lists.
- Group colours: one source — `lib/groupColor.ts` (events use it for subgroup events too).
- Delete orphans you replace; grep for importers first.

## Primitives contract (Task A2 produces; everyone else consumes)
```ts
// components/ui/page/index.ts re-exports all
PageHeader({ title: string; description?: string; actions?: ReactNode; back?: { href: string; label: string } })
Toolbar({ children: ReactNode; className?: string })            // glass pill row, wraps on phone
SearchField({ value, onChange, placeholder, label, debounceMs? = 0 })   // label = aria-label
Segmented<T extends string>({ options: { value: T; label: string; icon?: LucideIcon }[]; value: T; onChange(v: T): void; label: string })
Panel({ title?: string; icon?: LucideIcon; actions?: ReactNode; children; className?; as?: "section"|"div" })  // .glass rounded-[32px]
ListRow({ children; href?; onClick?; selected?; className? })   // .glass-item rounded-[22px], selected ring
SideNav({ items: { id: string; label: string; href: string; icon?: LucideIcon }[]; activeId: string; label: string }) // glass list, active ink pill; phone: horizontal scroll pills
TwoPane({ aside: ReactNode; children: ReactNode; asideWidth?: number = 300 }) // md+: grid aside|main ; phone: stacked
```

---

## Wave A (parallel)

### A1 — Backend: branding defaults follow the new palette
- Files: `backend/app/models/branding.py`, new migration `0033_branding_glass_defaults.py` (down_revision `0032_home_glass_bento`), `backend/tests/unit/migrations/test_branding_defaults_migration.py`, branding service tests if defaults are asserted.
- New defaults: `color_primary #10141A`, `color_primary_dark #E9ECF2`, `color_accent #3B5E9E`, `color_surface_light #F5F6F9`, `color_surface_dark #1A202A`, `color_text_light #10141A`, `color_text_dark #E9ECF2`, `font_family "Outfit"`, `font_family_mono` unchanged.
- Migration: change server defaults; `UPDATE community_branding SET <col>=<new> WHERE <col> = <old default>` per column (old: `#3b82f6`, `#2563eb`, `#C6B4F5` (case-insensitive, also `#8b5cf6`), `#ffffff`, `#1f2937`, `#111827`, `#f9fafb`, `Inter`) — customised values untouched.
- Tests: migration parent pin; model defaults equal the new values.

### A2 — Frontend primitives + base component restyle
- Create `components/ui/page/{PageHeader,Toolbar,SearchField,Segmented,Panel,ListRow,SideNav,TwoPane,index}.tsx` per contract; tests `tests/unit/ui/page/*.test.tsx` (render, aria, Segmented arrow-key + aria-pressed/role=radiogroup, SearchField debounce).
- Restyle (keep APIs): `ui/Card.tsx` (default tone → glass-item surface, rounded-[24px]; drop unused `featured`), `ui/EmptyState.tsx` (glyph in soft circle, ink-pill action), `ui/Tabs.tsx` (active = ink pill, list = glass pill), `ui/Drawer.tsx` + `ui/Modal.tsx` + shadcn dropdown/popover content (glass-solid surface, radius 24–28, edge `--nx-glass-edge`), `ui/Badge.tsx` (no `bg-accent` fill for default/accent tone → `bg-[var(--nx-blue)]/15 text-ink`), shadcn `--primary-foreground` alias → `var(--nx-bg)` in globals.css; `ConfirmDialog` drop `bg-accent text-white` override.
- Button: `primary` → ink pill `rounded-full`; `secondary` → `glass`. Keep variant names.
- Run full vitest; fix snapshot/class assertions you broke.

### A3 — Shell, nav, avatar menu, frame
- `Shell.tsx` main: `mx-auto w-full max-w-[1440px] px-4 md:px-8`; chat layout keeps full-bleed via its own layout (adjust `-mx` accordingly).
- `navItems.tsx`: `TOP_NAV` Home/Chat/Calendar/Photos(`/app/photos`)/Groups; `MORE_NAV` People(`/app/members`), Lists, Kudos, Saved(`/app/bookmarks`), Notifications(`/app/notifications`), Settings, Admin(adminOnly), Help (button → opens existing help/shortcuts surface; no route). Remove `PRIMARY_NAV` (update its tests). BottomTabBar derives from one array.
- `AvatarMenu`: glass content; items Profile(`/app/members/{me}`), Settings, Admin (only `isAdmin`), Keyboard shortcuts, Sign out; extract shared `useSignOut()` used by AvatarMenu + MoreSheet.
- Home page container: remove its own `max-w-[1400px]` (frame handles it).
- Tests: nav arrays, AvatarMenu hides Admin for members, BottomTabBar items.

### A4 — Feed and Home leftovers
- `PostCard`: surface → glass-item (via Card), hover subtle; `KudosCard`: drop purple — glass-item with `--nx-sun` accent bar + Trophy glyph; `HomeFeed`/`PostComposer`: composer collapsed to one line ("Share something with everyone") expanding on focus; audience radios become a compact `Segmented` inside the expanded composer *(import from components/ui/page once A2 lands; if absent, inline minimal pills and leave TODO-free note in report)*; "Send kudos" becomes a composer toolbar icon button (Trophy, aria-label "Send kudos"), floating lilac button removed.
- `HomeTile`: replace click re-dispatch with `useRouter().push` and add `vi.mock("next/navigation")` to the 5 tile/HomeTile tests.
- NeedsChips: RSVP link `?event=` (not `?e=`); prompt chip → `/app/prompts/{prompt_post_id}`.

---

## Wave B (parallel, after A merges) — each task: migrate to primitives, delete replaced/orphan code, tests updated, polish pass screenshots by orchestrator

### B1 — Chat
`components/chat/ChatLayout.tsx`, `chat-layout/*`, `ChannelList`, `MessageItem`, `Composer`, `MessageList` empty states, `FloatingChatDock`/`ChatLauncher`/`ChatHead` surfaces. TwoPane: glass aside (search field + Segmented "All | Groups | Direct" + rows reusing `components/home/tiles/ChatThreadRow` visuals via a shared `ThreadRow`), main glass panel with header, bubbles (others `--nx-bubble`, self ink pill), composer pill like InlineThread. "New message" = ink pill icon+label. Remove density toggle (keep compact as default) only if no tests require; otherwise keep. Delete `notifications/NotificationRow.tsx` is not yours.

### B2 — Calendar
`events-page/*`, `MonthCalendarLarge`, `WeekView`, `DayView`, `ListView`, `CalendarFilterBar`, `CalendarViewSwitcher`, `EventsSidePanel`, `EventRail`, `eventColors.ts`, `toneStyle.ts`. PageHeader("Calendar", actions: New event ink pill) + Toolbar(prev/Today/next + month label, Segmented Month/Week/Day/List, calendar filter popover). TwoPane-right layout: main glass grid; aside = Panel "Up next" (EventRail) + selected day list. Remove EventCountdown hero + CalendarWidget mini-month from the page (one navigator). Chips: soft fill of group colour (`groupColor`) at 22% + 3px left bar + ink text (AA). Delete orphans `events/MonthCalendar.tsx`, `events/EventList.tsx` (+tests). Event detail drawer surface glass.

### B3 — Photos (galleries + media consolidated)
New route `app/app/photos/page.tsx` → `components/photos/PhotosPage.tsx`: PageHeader("Photos", actions: Upload (ink) + New album (glass)) + Toolbar(SearchField, Segmented "Albums | All photos", sort Segmented Recent/Popular/Oldest for albums). Albums view = expand-image-cards (desktop: row of tall cover cards; hovered/focused card widens to show title, count, contributors, "Open album"; phone: accordion). All photos view = `useHomeMedia({limit:60})` masonry/grid of MediaThumb + Lightbox, upload via existing UploadZone (Panel). `app/app/galleries/page.tsx` and `app/app/media/page.tsx` → `redirect("/app/photos")` preserving `?gallery=` → `/app/photos?gallery=`. Add `app/app/galleries/[id]/page.tsx` redirect → `/app/photos?gallery=[id]`. GalleryDrawer/Lightbox surfaces glass. Consolidate GalleryGrid/GalleryMosaic into one `AlbumGrid` used by PhotosPage, MemberGalleriesTab, hub GalleriesTab. Remove `hooks/useMedia.ts` if still unused.

### B4 — Groups
`app/app/subgroups/page.tsx` (move UI to `components/subgroups/groups-page/GroupsPage.tsx`), `GroupMosaic`, `SubgroupCard`, `GroupHub`, `hub/*`, `CoverBand`. PageHeader("Groups", New group) + Toolbar(SearchField, Segmented All/Open/Private, "Mine" toggle) + responsive grid of glass group cards (cover image or colour wash from groupColor, name, description 2 lines, member avatars, Join/Open). GroupHub: compact cover band (≤220px, glass overlay title), SideNav/Segmented tabs (active ink), tab contents in Panels. Delete `SubgroupList.tsx`, `layout/GroupContextSwitcher.tsx` if unused.

### B5 — People (new) + profile
Backend: if no members directory endpoint suitable for non-admins exists, add `GET /api/v1/users/directory?q=&limit=&cursor=` (active, non-bot, community-scoped, block-filtered, privacy-aware: online/last_seen like home people) — check `GET /api/v1/users` first (users.py:152) and reuse if non-admin accessible. Frontend `app/app/members/page.tsx` → `components/members/PeopleDirectory.tsx`: PageHeader("People") + Toolbar(SearchField, Segmented All/Online/My groups) + grid of person cards (avatar ring, name, shared groups, status, Message/Profile). `members/[id]`: real profile — header card (avatar, name, @username, bio if available, shared groups, Message, Nudge, Block menu), Segmented Posts/Photos/Groups; no raw IDs.

### B6 — Settings + Admin
`SettingsTabs` → TwoPane + SideNav (glass), each tab body uses Panels/rows; PageHeader("Settings"). Admin: `AdminTabs` → TwoPane + SideNav including Storage, Retention, Plugins, Moderation as items (routes stay); single `AdminGate` replacing RetentionGate/ModerationGate/inline checks; PageHeader("Admin"). Settings Storage/Plugins tabs: remove `PluginsSettingsTab` empty shell if it has no function. Metrics tiles → Panels with stat rows (not white cards).

### B7 — Lists, Kudos, Saved, Notifications, Prompts, Post detail
Lists: PageChrome.PageHeader → shared PageHeader (keep breadcrumbs via `back`), ListCard glass, filters via Segmented. KudosWall: PageHeader + Toolbar (Segmented Newest/Oldest, group select) + grid of restyled KudosCard. Bookmarks → title "Saved". New `app/app/notifications/page.tsx` rendering the NotificationsDrawer list component full-width inside Panel (extract `NotificationList` shared by drawer + page); delete orphan `notifications/NotificationRow.tsx`. Prompts `[id]` + post `[id]`: PageHeader with back, Panels.

## Wave C — Verification
- C1 Playwright: `npm i -D @playwright/test` if missing; config `use.channel` unset + `launchOptions.executablePath` from `PW_CHROME` env; specs run against `BASE_URL=http://localhost:8090` (container): login, home tiles, chat send+receive (two contexts), calendar create+RSVP, photos upload, groups create/join, people search, settings pattern change persists, admin tabs reachable, phone nav.
- C2 Polish pass per section (orchestrator): screenshots desktop/phone × light/dark for every route; fix deltas.
- C3 Full suites, push branch, open PR.
