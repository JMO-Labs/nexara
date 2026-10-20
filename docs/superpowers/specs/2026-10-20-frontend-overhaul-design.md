# Frontend Overhaul — "Garden Club" Design

**Date:** 2026-10-20 · **Status:** Draft, pending user approval · **Owner:** sgtslaughta

## 1. Intent

Nexara's frontend works but has drifted: an unmaintained component library (MUI Joy beta), three
competing styling systems (Joy `sx` in 118 files, inline `style` in 44, CSS classes + `globals.css`),
duplicate components, oversized files, and a "Warm Editorial" look (Fraunces + terracotta on cream)
that reads as generic. The audience is the owner's own family and friends first; the app should feel
warm, specific, and built for phones.

The overhaul replaces the UI foundation and visual identity, rethinks the home/navigation experience
around a single live feed, and fills the UI gaps where the backend already has features.

## 2. Goals

1. New visual identity ("Garden Club", §5) in light and dark, WCAG 2.1 AA throughout.
2. Replace MUI Joy + Emotion with **Tailwind CSS + shadcn/ui (Radix primitives)**. One styling system.
3. Phone-first shell: bottom tab bar on phones, collapsible icon side nav on desktop.
4. Home becomes a **unified live feed** (posts + activity) in the center column (§6).
5. Every existing screen re-skinned and made phone-usable.
6. New UI for backend features that have none: **notifications inbox**, **admin Branding**.
   Notifications work on desktop and phone, in-app and as system (Web Push) notifications (§7).
7. Remove dead weight (§9). All files ≤ 400 lines.
8. Test coverage maintained or improved; CI pipeline green when the overhaul merges to `main`.

## 3. Non-goals

- No framework change. Next.js 16 App Router, React 19, TanStack Query v5, zustand, `lib/api/*`,
  `hooks/*`, next-intl, PWA/service worker all stay.
- No redesign of layouts for: events/calendar, galleries/media, chat, groups (subgroups hub),
  members, settings, admin, auth. These get the new skin + phone fixes, same structure.
- No new locales.
- Phase 2 leftovers (polls UI, kudos, bookmarks, birthdays, nudges, shared lists, moderation UI,
  retention UI), Phase 6 list templates, Phases 3–4: **out of scope** — each is its own later
  project with its own brainstorm. Exception: poll *cards in the feed* already rendered today must
  keep rendering (re-skinned); the poll creation UI is not built here.

## 4. Anti-goals (failure even if it "works")

- `main` broken at any point. Overhaul lives on its own branch until complete.
- Any Joy/Emotion code or dependency left at the end.
- The feed jumping under the reader's thumb while they read.
- The live feed leaking anything a viewer is not allowed to see (private/subgroup items, blocked users).
- Ambient decorative motion; motion that ignores `prefers-reduced-motion`.
- Looking like a generic SaaS card kit.

## 5. Visual system — "Garden Club" (decided)

Reference mockups: `.superpowers/brainstorm/*/content/visual-direction.html` (option C),
`garden-dark-desktop.html`, `live-feed.html` (option B). Local only, gitignored.

### Color tokens

| Token | Light | Dark ("night garden") | Use |
|---|---|---|---|
| `bg` | `#E9F1E4` pistachio | `#0E1F15` | page background |
| `surface` | `#FFFFFF` | `#16291D` | cards, posts |
| `surface-strong` | `#14301E` forest | `#1B3524` | featured cards, nav, tab bar |
| `ink` | `#14301E` | `#DCE9D8` | body text |
| `accent` | `#C6B4F5` lilac | `#C6B4F5` | active nav/tab, date chip, focus, highlights |
| `sun` | `#F2D16B` | `#C9A94A` | supporting fill (never text on light) |
| `leaf` | `#7BAE7F` | `#4E7F56` | supporting fill |
| `muted` | `#9DB8A2` | `#86A38C` | inactive icons/labels on `surface-strong` |

- Defined as CSS variables (`:root` / `.dark`) consumed by Tailwind theme + shadcn tokens.
- Dark mode toggled by `next-themes` (already installed) via `class` strategy; system default.
- Lilac is used as a fill/background with forest text, or as text only on `surface-strong`.
  Builder must verify every text/background pair hits AA (4.5:1 body, 3:1 large/UI).
- Photo tiles are dimmed slightly in dark mode.

### Type

- **Hanken Grotesk only**, self-hosted via `next/font/google`, weights 400 / 600 / 900.
  Replaces Fraunces, Geist, Geist Mono.
- Headlines: 900, tight leading (~0.92), negative tracking (~-0.03em). Large greeting on home.
- Body 400, emphasis 600. Sentence case everywhere; no all-caps labels.

### Shape and motion

- Large soft radii (16–28px), varying by hierarchy. Featured cards (`surface-strong`) have **one
  sharp corner** (bottom-left ~6px) — the signature shape.
- Motion only in response to user action (sheet open, RSVP confirm, reaction landing, new feed
  item sliding in). No entrance/ambient animations. Respect `prefers-reduced-motion`.
  framer-motion stays, used sparingly.
- Icons: **Lucide** (`lucide-react`). Heroicons removed.

### Community branding

Admin Branding screen (new, uses existing `branding` router) lets admins set **logo, community
name, accent color** only. Rest of palette locked. Accent picker rejects colors that fail AA
contrast against `surface-strong` and against forest text. Accent applied by overriding the
`accent` CSS variable at runtime.

## 6. Layout and the unified feed (decided)

### Shell

- **Phone (< md):** bottom tab bar on `surface-strong`, floating pill (rounded, inset from edges):
  **Home, Chat, Calendar, Groups, More**. "More" opens a sheet with: Galleries, Media, Members,
  Notifications, Settings, Admin (if admin), Help, Sign out.
- **Desktop (≥ md):** slim icon-only side nav (`surface-strong`), expands to show labels on hover
  or keyboard focus. Community logo at top. Same destinations.
- **Chat on desktop:** floating chat dock only (existing `chatDock` store). No right rail.
- Command palette (single one, §9) and notifications bell remain globally reachable.

### Home

- **Phone:** greeting → "Next up" featured event card → unified feed.
- **Desktop:** greeting → center column unified feed → narrow right widget column.
- **Widget column (desktop):** vertical list of existing widgets (upcoming events, my groups,
  media, quick actions; feed/activity widgets are retired since the feed is the page).
  Users can **reorder and hide** widgets via dnd-kit (already installed).
  **react-grid-layout is deleted** along with `WidgetGrid`, `RightRail`, `dashboardRail` and
  `widgetDrag` stores, and the grid-specific layout code.

### Unified feed

- One stream. **Composer at top.** Posts and polls render as full cards; small events (RSVP,
  reaction, join, upload, comment) render as **one-line entries** (avatar, sentence, relative time).
- Merges today's Feed (posts) and Activity (activity_event) surfaces.
- **Live:** new items arrive over the existing SSE stream. Each event appears as it happens;
  repeats by the same actor on the same target within **10 seconds** collapse into one entry.
- **Arrival behavior:** if the viewer is at the top, new items slide in (brief lilac highlight);
  if scrolled down, a **"N new" pill** appears and nothing shifts until tapped.
- **Privacy:** feed items, both on initial load and over SSE, are filtered **server-side** by the
  same visibility model (community / subgroup / private) and `apply_block_filter`. The frontend
  never filters for privacy.
- Infinite scroll (cursor pagination) going back in time.

## 7. Notifications inbox (decided: full rethink, sequenced)

- New page `/app/notifications` + bell becomes a preview linking to it.
- Built **after** Notifications Plan A (backend foundation, `docs/superpowers/plans/2026-05-02-notifications-plan-a-foundation.md`)
  lands. Component shape follows the notifications refactor spec's frontend section
  (`docs/superpowers/specs/2026-05-02-notifications-refactor-design.md`).
- Backend Plans A/B run in parallel with frontend phases 0–2 below.

### Inbox on both form factors (decided)

- **Phone:** bell in the top bar opens the full inbox page.
- **Desktop:** bell opens a popover preview (latest items, mark read) with a link to the full page.

### System notifications — Web Push on desktop and phone (decided)

- Uses the existing `push` router / service worker. Works with Nexara closed.
- **Deep links:** tapping a notification opens the exact post, event, or chat.
- **Permission prompt in context:** never on page load. Offer "Turn on notifications" after a
  meaningful action (e.g. first RSVP, first chat message); also available in Settings → Push.
- **iPhone:** push requires the PWA be added to the Home Screen. On iOS Safari (not installed),
  the prompt first shows add-to-Home-Screen instructions.
- Pushes are sent only for types the user has enabled; the per-type controls follow the
  notifications refactor spec's preference model.

## 8. Migration approach (decided)

**Full replacement, no coexistence.** Joy, Emotion and the old theme are removed in step 1. No
compatibility layer between Joy and Tailwind. Work happens on a long-lived `feat/frontend-overhaul`
branch (sub-branches per step merge into it); it merges to `main` once complete and green.
Expect the branch's UI to be partly broken mid-way; `main` keeps the old UI until the merge.

0. **Precondition:** commit and merge the uncommitted `polish/phase-5-motion` work to `main`,
   then branch `feat/frontend-overhaul` from `main`.
1. **Foundation:** remove Joy/Emotion/old theme and all §9 dependencies; Tailwind + shadcn setup,
   tokens (§5), font, Lucide, theme switching, base shadcn components (button, input, dialog,
   sheet, tabs, dropdown, tooltip, toast, avatar, badge, card, skeleton) replacing
   `components/ui/*` with the same export names where practical to limit churn.
2. **Shell:** bottom tab bar, side nav, More sheet, app layout, command palette, bell.
3. **Home + unified feed** (§6), including backend work it needs.
4. **Re-skin areas**, one per branch: feed/post detail, chat, events/calendar, galleries/media,
   subgroups, members, settings, admin (+ Branding screen), auth/onboarding/help/offline.
5. **Notifications inbox** (after backend Plan A).
6. **Final sweep:** grep confirms zero `@mui`/`@emotion`/`sx=` usages; full e2e suite pass;
   merge `feat/frontend-overhaul` to `main` (minor version bump).

Each step: tests for that area rewritten (behavior assertions kept, Joy-markup assertions replaced).
Each sub-branch merge: that area's tests + `eslint` on touched files pass. ~202 files import
Joy/Emotion today, so full `tsc`, full test suite and `next build` stay red until the last area
moves. At final merge: everything green, coverage ≥ `main`, full GitLab CI passes.

## 9. Cleanup (decided)

- Remove: `@mui/material` (unused), `@mui/joy`, Emotion, `@heroicons/react`, `react-slick`,
  `slick-carousel`, `@types/react-slick`, `react-grid-layout`. Keep `embla-carousel-react`.
- One command palette: keep `search/GlobalCommandPalette.tsx`, delete `ui/CommandPalette.tsx`.
- Split files > 400 lines: `app/app/galleries/page.tsx` (804), `events/EventCreateModal.tsx` (609),
  `events/EventDetailPanel.tsx` (545), `chat/ChatLayout.tsx` (510),
  `events/CalendarSubscriptionsPanel.tsx` (501), `admin/PromptsTab.tsx` (472),
  `app/app/events/page.tsx` (462), `events/CalendarFilterBar.tsx` (416).
- Fix stale docs: root `CLAUDE.md` Frontend section and `plans/project_plan.md` say Nuxt; they
  should say Next.js 16 + Tailwind/shadcn.

## 10. Constraints

- WCAG 2.1 AA: ARIA labels, full keyboard nav (side nav expand on focus, tab bar, sheets),
  visible focus ring (lilac), contrast-checked tokens.
- Files ≤ 400 lines; Doxygen-style file/component headers per repo convention.
- Backend changes follow strict layering (router → service → repo), `community_id` scoping,
  error envelope.
- Conventional Commits, semver. GitLab CI stages must pass before each merge.

## 11. Builder's calls (decided by Claude, not the user — flag if wrong)

- **Widget prefs storage:** reuse existing `user_settings.home_layout` JSONB column with a new
  shape `{ order: string[], hidden: string[] }` instead of a new migration; old grid-shaped values
  ignored/reset on read.
- Tailwind v4 (current) with shadcn's Tailwind-v4 setup.
- Long-lived `feat/frontend-overhaul` branch so `main` stays usable during the full replacement.
- "Next up" card = the viewer's nearest upcoming event they RSVP'd yes/maybe to, else nearest
  visible event, else hidden.
- Phone home has no widget column.
- **Feed endpoint:** new server endpoint `GET /api/v1/home/feed` returning posts + activity in
  one cursor-paginated stream (server already must filter for privacy, so merge there). Existing
  posts/activity endpoints stay for other screens.
- **10-second collapse + live:** collapse happens only server-side (activity aggregation window
  10s for the home feed). Live = server emits a lightweight `feed_ping` SSE event to the item's
  audience only; client refetches the feed head and slides in unseen ids. No client-side merge.
- **SSE audience scoping (bug fix):** existing `feed_update` events broadcast to the whole
  community (`CommunityTarget`) regardless of visibility. All feed events are re-targeted to
  resolved recipients (`UserTarget` per viewer allowed to see the item, minus block relations).
  ponytail ceiling: O(members) per event; move filtering into the connection manager if
  communities grow beyond hundreds.
- **Old widget layouts:** grid-shaped `home_layout` values reset to default order on first read.
  No data migration.
- **Sequencing:** frontend phases 0–4 do not block on Notifications Plan A. Inbox (phase 5)
  starts only once Plan A is merged.
- **Phone chat:** Chat tab opens the full-screen chat page; the floating dock is desktop only.
- **Phone search + bell:** slim top bar on phone screens with search (opens command palette)
  and the notifications bell.

## 12. Left to the builder

- Exact shadcn component set beyond the base list; component file organization under
  `components/ui/`.
- Feed cursor format and collapse-key details, as long as §6 privacy and arrival behavior hold.
- Exact spacing/type scale values within §5.
- Per-area test strategy details.
