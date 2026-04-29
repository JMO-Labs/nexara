# Home Redesign — QA Verification Punch List

Based on the "Verification" section of the home redesign plan.
Run these after `cd deploy && docker compose up -d` with the dev server.

## Polish pass (phase-5-motion)

- **ConfirmDialog now used everywhere**: `window.confirm` removed from all 7 call sites
  (WidgetFrame remove, WidgetGallery reset, PostCard delete, ChatLayout remove DM,
  MembersList remove member, galleries delete gallery, galleries remove item).
  OS dialogs are fully replaced by the in-app MUI Joy modal (`ConfirmDialog` mounted in Shell).
- **Default layout changed**: feed(lg=8) | upcoming-events(md=4) / media-carousel(full) / activity(sm) + quick-actions(sm) + my-groups(md)
- **Widget resize controls**: S/M/L/F buttons in lower-left footer of each widget frame.
- **Chat dock sizing**: ChatHead cards increased to 480×560 px.
- **Dark mode text**: WidgetFrame title uses `var(--joy-palette-text-primary)` Joy token.
- **Size grid**: md=4col, lg=8col on the 12-column grid (changed from md=6, lg=9).

| # | Step | Status |
|---|------|--------|
| 1 | Home page loads without JS errors in browser console | ⏳ manual |
| 2 | Default widget layout renders (6 built-in widgets visible) | ⏳ manual |
| 3 | Drag a widget to a new position; reload — order persists (layout stored in user settings) | ⏳ manual |
| 4 | Collapse a widget via the chevron button; reload — collapsed state persists | ⏳ manual |
| 5 | Remove a widget via the × button; confirm dialog appears; widget disappears | ⏳ manual |
| 6 | "+ Add widget" FAB opens the WidgetGallery drawer; can add a removed widget back | ⏳ manual |
| 7 | "Reset to default" in WidgetGallery restores the default 6-widget layout | ⏳ manual |
| 8 | WelcomeBanner renders on first visit; dismisses on click and does not reappear | ⏳ manual |
| 9 | UpcomingEventsWidget shows events from backend `/home/upcoming-events` endpoint | ⏳ manual |
| 10 | ActivityWidget renders recent feed items from `/home/activity` | ⏳ manual |
| 11 | MediaCarouselWidget renders gallery images via Carousel component | ⏳ manual |
| 12 | MyGroupsWidget lists the current user's subgroups | ⏳ manual |
| 13 | QuickActionsWidget buttons navigate to correct routes | ⏳ manual |
| 14 | FeedWidget renders posts inline with SourceBadge pills | ⏳ manual |
| 15 | SourceBadge community pill shown for community posts; subgroup pill links to `/app/subgroups/<slug>` | ⏳ manual |
| 16 | FloatingChatDock is hidden on `/app/chat` route | ⏳ manual |
| 17 | FloatingChatDock shows ChatLauncher pill; clicking it opens channel/DM list | ⏳ manual |
| 18 | Opening a thread from ChatLauncher shows ChatHead card; Minimize/Close work | ⏳ manual |
| 19 | Keyboard navigation: Tab reaches drag handle, collapse toggle, remove button, carousel arrows | ⏳ manual |
| 20 | Focus rings visible on all interactive elements (indigo outline) | ⏳ manual |
| 21 | With `prefers-reduced-motion: reduce` in DevTools: Collapsible/WidgetFrame open/close instantly; ChatHead slide skipped | ⏳ manual |
| 22 | Mobile viewport (≤640 px): WidgetGallery FAB still reachable; ChatDock shows bottom drawer only | ⏳ manual |
| 23 | Dark mode: all widgets, badges, and chat components render without contrast issues | ⏳ manual |
| 24 | Backend `/api/v1/home/upcoming-events` and `/api/v1/home/activity` return 200 for authenticated user | auto-tested ✅ (unit tests cover service layer) |
| 25 | `npx vitest run` — 406 pass, 5 skipped (pre-existing), 0 fail | auto-tested ✅ |
| 26 | `pytest -q --ignore=tests/integration` — 1111 pass | auto-tested ✅ |
