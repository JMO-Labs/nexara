# Home: Glass Bento — Spec

Date: 2026-11-19 · Mockup: `docs/superpowers/specs/2026-11-19-home-glass-bento-mockup.html`
(published: https://claude.ai/artifact/Bw6SpGSQUA59L5gFB3Bv8c)

## Goal
The signed-in home screen (`/app`) is the user's primary screen. It shows everything that involves the
user, across every group they belong to, at a glance — without feeling busy. Suits all ages.
Primary focus: chat, feed, photos, upcoming events.

## Layout (desktop ≥ md)
```
top bar: logo+wordmark | pill nav (Home Feed Chat Calendar Photos Groups More▾) | Create · Search · Bell · Avatar
greeting row: "Good evening, {first name}" + date        | people strip (glass pill)
strip row:   [scope pills: Everything · group…]          | [Needs you: chips…] (scrolls horizontally, never wraps)
bento (fixed height ~800px):
  ┌ Feed (1.3fr, spans 2 rows) ┬ Chats (1fr, spans 2 rows) ┬ Up next (.8fr) ┐
  │ composer, new-posts pill,  │ ranked threads, one open,  ├ Photos         ┤
  │ posts scroll inside panel  │ inline reply               │ 2x2 hero + 5 sq │
```
- Left rail removed. Quick-create = one "Create" button (post, event, upload, list).
- Customize / widget drag-and-drop removed from Home (fixed layout v1).

## Phone (< md)
- Bottom tab bar pinned: Home, Chat (unread badge), Create (center), Calendar, Photos.
- Top bar: logo, Create (+), Bell, Avatar.
- Order: greeting → people (h-scroll) → scope pills (h-scroll) → Needs you (h-scroll) → sections.
- Sections Up next, Chats, Photos, Feed are an accordion: collapsed header shows icon, title, one-line
  summary, count badge (red = needs you, blue = new), chevron. Only one open at a time; tapping the open
  one closes it. Default open: Chats if any thread mentions the user, else Up next.

## Scope ("connected across groups")
- Default **Everything**: every tile aggregates across all of the user's groups (community + subgroups + DMs).
- Every item shows its group color dot + name.
- Scope pills (Everything + each group the user belongs to) filter all tiles at once (client-side).
- Group color: deterministic from group id over a fixed 6-color palette (no new DB column).

## Tiles
- **Feed**: existing home feed items (posts, polls, kudos, activity) + composer + "N new posts" pill.
- **Chats**: thread ranking — (1) threads that @mention the user since last read, (2) unread threads by
  recency, (3) everything else by recency. Muted threads excluded (if mute exists). Top 4 shown + "See all chats".
  Accordion: one thread open (default = top-ranked) showing last 3 messages + reply box. Sending marks read.
- **Up next**: next 3 upcoming events (date block, title, time/place, ✓ going or RSVP button).
- **Photos**: newest album/batch: title, "N new", 2x2 hero + 5 squares, last square "+N". Images
  `object-fit: cover`, fixed geometry. No hover shimmer on photos.

## People strip
- Up to 10 people sharing a group with the user, ordered: online now → birthday within 7 days (cake marker,
  respects `show_birthday_to`) → most recently active.
- Ring color = group most shared with them. Hover/tap → connection card: name, shared groups, shared events
  in last 30 days, status line, [Message] [Profile]. A dashed "Add how you know {first}" slot is shown but
  inert (relationship labels are a later feature).

## Needs you
Chips, hidden when empty, each links out: pending RSVPs (upcoming events, no RSVP), open polls not voted
(last 7 days), unanswered active prompt, open list items due within 7 days. Urgent chips (RSVP, list) use red glyph.

## Visual system
- Font: Outfit (Google). Palette: ink #10141A, ground #E4E4E4, blue #83A2DB, red #CE6969, white.
  Dark: ground #0D1117, ink #E9ECF2, blue #8FAEE6, red #DB7B7B.
- Glass panels: translucent fill + `backdrop-filter: blur(26px) saturate(1.6)`, 1px light edge, inset top highlight.
  Radius: panels 32px, items 22–24px, pills full.
- Active nav / selected pill / primary button: solid ink pill (inverted in dark).
- Background: brand gradient (blue + red soft blobs) + pattern overlay (mask, ink at ~7–9%).
  Patterns: none, dots, topographic, contour (default), waves, grain. Community default set by admin
  (branding); each user may override (Settings → Appearance).
- **Reduce transparency**: user setting + auto on `prefers-reduced-transparency`; panels become solid.
- All text on glass meets WCAG AA.
- Logo: house outline + N over three overlapping circles (assets in `frontend/public/brand/`);
  theme-aware inline mark in header. Wordmark: **nex** semibold + ara light.

## Motion (framer-motion)
1. One staggered entrance of the top bar, greeting, strip, and tiles on first load.
2. Layout animation when live items arrive (new message slides in, new-posts pill pops).
3. Tile → page expand (shared layout) when opening Chat/Feed/Photos/Calendar from a tile header.
4. Hover: pointer-following sheen on glass panels; light sweep on Create button and RSVP button only.
All disabled under `prefers-reduced-motion`; hover effects only for `(hover: hover)`.

## Out of scope (tickets)
Relationship labels; cover-photo background; per-user tile show/hide; muting threads if not already modeled.
