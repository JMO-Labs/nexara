# App Unification — Spec (Phase 2)

Date: 2026-11-19. Follows `2026-11-19-home-glass-bento.md`. Goal: every signed-in page feels like the same
app as Home — one frame, one header, one toolbar, one surface system, no leftover Garden Club styling.
Works end to end in the production container.

## 1. Page frame
- Content width: `max-w-[1440px] mx-auto`, side padding 16px (phone) / 32px (md+). Home uses the same frame
  (it is currently narrower than the mockup).
- Vertical rhythm: header → toolbar → content, gap 16–20px.

## 2. Shared primitives (`components/ui/page/`)
| Primitive | Replaces | Look |
|---|---|---|
| `PageHeader({title, description?, actions?, back?})` | `PageMasthead` hero titles, mono uppercase subtitles | h1 32px (md 40px) weight 500 tracking -0.02em; description 15px muted, sentence case; actions right-aligned |
| `Toolbar({children})` | ad-hoc search bars + filter rows | one glass pill row; wraps on phone into two rows |
| `SearchField` | per-page search inputs | glass-item input with search glyph, 40px tall |
| `Segmented({options, value, onChange})` | Recent/Popular/Oldest, ALL/OPEN/PRIVATE, Month/Week/Day/List, filter pills | pills inside a glass group; active = ink pill (`bg-surface-strong text-bg`) like Home's scope bar |
| `Panel({title?, icon?, actions?, children})` | bespoke page panels/cards | `.glass` radius 32px, header like HomeTile desktop header |
| `ListRow` | assorted list items | `.glass-item` radius 20–24px |
| `EmptyState` (restyle existing) | — | glyph in soft circle, title, one sentence, one ink-pill action |
| `TwoPane({aside, children})` | chat sidebar, settings/admin tabs, events side panel | glass aside 300px + glass main; phone: aside becomes a list page / sheet |

Buttons: primary = ink pill (`bg-surface-strong text-bg`, rounded-full); secondary = `glass` variant; no
bright blue or lilac fills anywhere. Status colours only via `--nx-blue/red/ok`.

## 3. Pages
- **Home**: frame width; feed posts render as glass items (PostCard surface → glass-item); composer collapses to
  one line until focused; kudos becomes a composer action, not a floating lilac button.
- **Chat**: TwoPane — glass thread list (same row component as Home's chat tile) + glass thread panel with
  bubbles matching InlineThread; composer pill. Connects (same-origin WS).
- **Calendar** (`/app/events`): PageHeader + Toolbar (month nav, Today, Segmented Month/Week/Day/List, calendar
  filter) + TwoPane (glass month grid; aside = "Up next" + selected day). Event chips use group colour with
  readable ink text. Remove the countdown hero and duplicated mini-month.
- **Photos** (`/app/photos`, consolidates Galleries + Media): Segmented "Albums | All photos". Albums use the
  expand-image-card pattern (desktop row expands on hover/focus; phone accordion). Old `/app/galleries` and
  `/app/media` redirect.
- **Groups**: PageHeader + Toolbar (search, Segmented All/Open/Private) + card grid of glass group cards
  (cover, colour dot, members, Join). Group hub pages use Panel + Segmented tabs.
- **People** (`/app/members`, new index): searchable directory of community members with the connection info
  from Home's people strip; profile page `/app/members/[id]` restyled.
- **Lists**, **Kudos**, **Bookmarks** (as "Saved"), **Notifications**, **Prompts**: PageHeader + Toolbar + Panel/ListRow.
- **Settings** and **Admin**: TwoPane with glass tab list; Admin reachable from avatar menu and More.
- Avatar menu: Profile, Settings, Admin (admins), Theme, Sign out.

## 4. Consolidation
- Galleries + Media → Photos (one nav entry, two views).
- Notifications page reuses the drawer's list component.
- Bookmarks renamed "Saved".
- Nav: Home · Chat · Calendar · Photos · Groups · More (People, Lists, Kudos, Saved, Prompts, Notifications, Settings, Admin, Help).

## 5. Quality bar
- No `PageMasthead`, `font-mono uppercase` labels, `bg-blue-*`/lilac fills, or hardcoded hex in components.
- Every page: designed empty state, loading skeleton in glass, phone layout without horizontal scroll, AA contrast.
- E2E: Playwright runs against the production container (system Chrome) covering login, home, chat send,
  calendar create/RSVP, photos, groups, people, settings, admin.
- After each section: polish pass = screenshot desktop+phone, light+dark, fix what's off.
