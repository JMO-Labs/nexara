# Frontend Overhaul P3–P6 — Re-skin Remaining Areas

> **For agentic workers:** Run phase by phase. Each task is a re-skin of the listed files to Garden Club (Tailwind v4 + shadcn) with identical behavior, executed by one implementer + one reviewer. Stop after each phase for the human browser check.

**Goal:** Remove every remaining MUI Joy / Emotion / Heroicons import, one area at a time, keeping behavior, so every route works in the new design.

**Spec:** `docs/superpowers/specs/2026-10-20-frontend-overhaul-design.md` · **Index:** `…-frontend-overhaul-index.md` · **Global Constraints:** P1 + P2 plans apply in full.

## Shared rules (every task)

- Behavior, props, routes, data hooks and API calls unchanged unless the task says otherwise. Delete dead code you find; do not add features.
- Use `@/components/ui` (barrel) primitives; raw shadcn under `components/ui/shadcn/`. Do not edit `components/ui/*` — if a primitive is missing, report it (P3 Task 0 pre-installs the likely ones).
- Joy → Tailwind mapping: `Box/Stack/Sheet` → `div` with flex/gap utilities; `Typography level=h*` → semantic `h1–h4` with Hanken 900 for h1/h2, 600 for h3/h4; `body-sm` → `text-sm text-muted`; `Chip` → `Badge`/`Chip`; `Modal`/`Drawer`/`Tabs`/`Select`/`Input`/`Button`/`IconButton`/`Tooltip`/`Avatar` → same-named ui primitives (check their props in `components/ui/*.tsx` — **Avatar needs `name`**, Button variants are `primary|secondary|ghost|outline|destructive`, sizes `sm|md|lg`); `CircularProgress` → Lucide `Loader2` with `motion-safe:animate-spin` + `role="status"`; `Alert` → `div role="alert"` styled `rounded-2xl bg-surface p-3` (+ `border-l-4 border-[color]`); `sx` → classes; Heroicons → nearest Lucide icon.
- Files ≤ 400 lines: split oversized files into a sibling folder (`<area>/<component-name>/*.tsx`).
- Phone first: every screen usable at 390px (no horizontal scroll, tap targets ≥ 44px).
- Tests: migrate the listed tests off Joy (drop `CssVarsProvider`/`joy-theme`; keep behavior assertions; drop Joy-markup assertions). Add a test for any behavior you had to restructure. TDD for new behavior.
- Untrusted links → `safeInternalLink`; API path params → `seg()` (already in `lib/api`).
- Verify before reporting: `node scripts/route-check.mjs <task routes>` exits 0 (when all files on that route belong to finished tasks); `npx vitest run <task tests>` passes; `npx eslint <task files>` 0 errors.
- Do not commit; do not npm install (except P3 Task 0).

---

## P3 — Chat + post detail

**Routes:** `app/app/chat/page.tsx`, `app/app/chat/[channelId]/page.tsx`, `app/app/post/[id]/page.tsx`

- **P3.0 Primitives pre-install (only task allowed to npm):** `npx shadcn@latest add switch checkbox radio-group popover table progress separator scroll-area toggle-group label --yes`; ensure files land in `components/ui/shadcn/` (move + fix imports if not; never overwrite existing customised files — answer "no" to overwrite prompts). Export thin wrappers from `components/ui/` only for `Switch`, `Checkbox`, `Popover` (+ `PopoverTrigger`, `PopoverContent`) via `index.ts`, each with a minimal test. Runs alone before the rest of P3.
- **P3.1 Chat page:** `app/app/chat/layout.tsx`, `app/app/chat/page.tsx`, `app/app/chat/[channelId]/page.tsx`, `components/chat/ChatLayout.tsx` (513 → split into `components/chat/chat-layout/*`), `ChannelList.tsx`, `NewDmModal.tsx`; tests `tests/unit/chat/ChannelList.test.tsx` + any ChatLayout tests. Behavior: desktop two-pane (channel list 280px + conversation); phone: `/app/chat` shows channel list full screen, `/app/chat/[channelId]` shows conversation full screen with a back `IconButton aria-label="Back to channels"`. Reuse P2's `MessageList`, `MessageItem`, `Composer`, `TypingIndicator`.
- **P3.2 Post detail:** `app/app/post/[id]/page.tsx`, `components/feed/FeedView.tsx` (re-skin if still imported anywhere, else delete it and its tests). Post detail = `PostCard` expanded + `CommentThread`, back link to `/app`.

## P4 — Events / calendar

**Routes:** `app/app/events/page.tsx`

- **P4.1 Page + filters:** `app/app/events/page.tsx` (463 → split under `components/events/events-page/*`), `CalendarFilterBar.tsx` (428 → split), `CalendarViewSwitcher.tsx` (use `toggle-group`), `EventRail.tsx`; tests `CalendarViewSwitcher.test.tsx`. Phone: filters collapse into a `Drawer side="bottom"` opened by a "Filters" button; view switcher stays visible.
- **P4.2 Calendar views:** `MonthCalendarLarge.tsx`, `MonthCalendar.tsx`, `WeekView.tsx`, `DayView.tsx`; tests `WeekView.test.tsx` (+ add one month-grid keyboard test: arrow keys move day focus, Enter selects). Today = `bg-accent text-surface-strong` date chip; event chips keep their event colors (`eventColors.ts`) with AA text; phone month view shows dots, tapping a day lists its events below.
- **P4.3 Lists + subscriptions:** `ListView.tsx`, `EventCard.tsx`, `EventList.tsx`, `EventCountdown.tsx`, `CalendarSubscriptionsPanel.tsx` (502 → split; also mounted by settings); tests `EventCard.test.tsx`, `EventCountdown.test.tsx`, `CalendarSubscriptionsPanel.test.tsx`.

## P5 — Galleries, media, groups, members

**Routes:** `app/app/galleries/page.tsx`, `app/app/media/page.tsx`, `app/app/subgroups/page.tsx`, `app/app/subgroups/[slug]/page.tsx`, `app/app/members/[id]/page.tsx`

- **P5.1 Galleries page:** `app/app/galleries/page.tsx` (915 → split under `components/galleries/galleries-page/*`), `GallerySearchBar.tsx`, `GallerySortSelect.tsx`; tests `GallerySearchBar.test.tsx`, `GallerySortSelect.test.tsx`.
- **P5.2 Gallery parts + member page:** `GalleryCard.tsx`, `GalleryGrid.tsx`, `GalleryUpload.tsx`, `GalleryUploadModal.tsx`, `Lightbox.tsx` (focus trap, Esc closes, ←/→ navigate, `aria-label` per image), `app/app/members/[id]/page.tsx`, `components/members/MemberGalleriesTab.tsx`; tests `GalleryCard`, `GalleryUpload`, `Lightbox`, `MemberGalleriesTab`.
- **P5.3 Media:** `app/app/media/page.tsx`, `components/media/{MediaCard,MediaGrid,UploadZone}.tsx`; test `MediaCard.test.tsx`. UploadZone keeps drag-and-drop **and** a visible "Choose files" button (keyboard path).
- **P5.4 Groups list:** `app/app/subgroups/page.tsx` (resolve its TODO: add `is_member` to the `Subgroup` type only if the API already returns it, else leave the TODO), `CreateSubgroupModal.tsx` (414 → split), `SubgroupCard.tsx`, `SubgroupList.tsx`, `MembersList.tsx`; tests `SubgroupCard`, `MembersList`.
- **P5.5 Group hub:** `components/subgroups/hub/{CoverBand,GroupChatPanel,GroupHub,MemberOnlyGate,EventsTab,GalleriesTab,MediaTab,OverviewTab,PostsTab,SettingsTab}.tsx`, `hub/tabs.ts`; tests `GroupHub`, `SettingsTab`, `tests/unit/components/EventsTab.test.tsx`. Tabs scroll horizontally on phone; cover band uses the group's visual (`lib/groupVisuals.ts`).

## P6 — Settings, admin, branding, auth leftovers

**Routes:** `app/app/settings/page.tsx`, `app/app/admin/page.tsx`, `app/(auth)/{register,callback,magic-link,magic-link/verify,reset-password,two-factor}/page.tsx`, `app/page.tsx`, `app/offline/page.tsx`

- **P6.1 Settings:** `components/settings/{SettingsTabs,AccountTab,AppearanceTab,NotificationsTab,ProfileTab,PushSubscriptionRow,StorageTab}.tsx` + `app/app/settings/page.tsx`; tests `AccountTab`, `AppearanceTab`, `NotificationsTab`, `ProfileTab`. AppearanceTab: theme choice System / Light / Dark via next-themes `setTheme` (radio-group). Toggles use `Switch`. On phone, tabs become a list → detail pattern.
- **P6.2 Admin A:** `app/app/admin/page.tsx`, `components/admin/{AdminTabs,AdminSettingsTab,AuditLogTab,InterestsTab,InvitesTab,MetricsTab}.tsx`. Tables use shadcn `table` and collapse to stacked rows on phone.
- **P6.3 Admin B:** `components/admin/{PromptsTab (483 → split),SsoTab,UsersTab}.tsx`.
- **P6.4 Branding (new feature, spec §5):** backend `branding` router already exists — read it. Create `lib/api/branding.ts` (`getBranding()`, `updateBranding(body)` matching the router), `hooks/useBranding.ts`, `components/admin/BrandingTab.tsx` (name, logo upload/URL per backend support, accent color `<input type="color">` + hex field). Accent is rejected with an inline error unless `contrastRatio(accent, palette.light["surface-strong"]) >= 4.5` **and** `contrastRatio(palette.light["surface-strong"], accent) >= 4.5` (forest text on accent) — use `lib/contrast.ts` + `theme/palette.ts`; mirror the same check server-side if the router accepts arbitrary colors (422 with the error envelope). Runtime: `components/layout/BrandingStyle.tsx` mounted in `Shell` sets `--nx-accent` on `document.documentElement` from branding and shows the logo/name in `SideNav`/`TopBar`. Add the tab to `AdminTabs` (coordinate: P6.2 owns `AdminTabs.tsx`; P6.4 only appends one tab entry after P6.2 finishes → run P6.4 after P6.2). Tests: AA rejection, accepted color applied to CSS var, server 422 path.
- **P6.5 Auth leftovers + public pages:** `app/(auth)/{register,callback,magic-link,magic-link/verify,reset-password,two-factor}/page.tsx`, `app/page.tsx` (landing: redirect signed-in users to `/app`, else a minimal Garden Club welcome with "Sign in"), `app/offline/page.tsx`. Reuse the P2 login layout. `next` params via `safeInternalLink`.

## Phase gate (each phase)

1. `node scripts/route-check.mjs <phase routes…>` → exit 0.
2. `npx vitest run` over the phase's test dirs → pass; `npx eslint <phase files>` → 0 errors.
3. `next dev -p 3100`; for each phase route `curl --cookie nx_session=1` → 200 (dynamic segments: use any id; 200/404 page render, not a compile error); dev log has no "Module not found"/compile errors; stop the server by PID.
4. P6 only: also `cd backend && ruff check . && pytest -q` if backend touched.
5. Whole-phase review (security, a11y, behavior parity, phone layout).
6. Human browser check.
