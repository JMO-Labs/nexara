# Frontend Overhaul — Phase Index

> **For agentic workers:** This is the roadmap, not an executable plan. Each phase gets its own
> detailed plan file (`2026-10-20-frontend-overhaul-pN-<name>.md`), written when the previous
> phase is merged into `feat/frontend-overhaul`, against the code as it then stands.

**Spec:** `docs/superpowers/specs/2026-10-20-frontend-overhaul-design.md`

**Branching:** `main` ← `feat/frontend-overhaul` ← `feat/fo-pN-<name>` (one per phase).

| # | Phase | Spec § | Depends on | Detailed plan |
|---|-------|--------|-----------|---------------|
| P0 | Merge `polish/phase-5-motion` to `main`; branch `feat/frontend-overhaul` | §8.0 | — | in P1 plan, Task 0 |
| P1 | Foundation + shell: remove Joy/§9 deps, Tailwind v4 + shadcn, tokens, font, Lucide, `components/ui/*` rebuilt, side nav, bottom tab bar, More sheet, top bar | §5, §6 Shell, §8.1–2, §9 | P0 | `…-p1-foundation-shell.md` ✅ done |
| P2 | Home + unified feed: `GET /api/v1/home/feed` (BE), SSE live merge, 10s collapse, N-new pill, Next-up card, widget column (dnd-kit reorder/hide, `home_layout` new shape), delete RGL grid/RightRail/dashboardRail/widgetDrag; **SSE audience fix**, `feed_ping`; **pulled in:** PostComposer, chat dock children, Event/Gallery create modals, login page | §6 Home, Feed, §11 | P1 | `…-p2-home-feed.md` ✅ written |
| P3 | Re-skin: feed post detail + comments + reactions + poll cards; chat (split `ChatLayout.tsx` 510; phone full-screen; dock desktop-only) | §8.4 | P1 (P2 for PostCard reuse) | pending |
| P4 | Re-skin: events/calendar. Split `EventCreateModal` 609, `EventDetailPanel` 545, `CalendarSubscriptionsPanel` 501, `events/page.tsx` 462, `CalendarFilterBar` 416 | §8.4, §9 | P1 | pending |
| P5 | Re-skin: galleries/media (split `galleries/page.tsx` 804, embla only), subgroups hub, members | §8.4, §9 | P1 | pending |
| P6 | Re-skin: settings, admin (split `PromptsTab` 472) + **new Branding tab** (logo/name/accent, AA-checked), auth, onboarding, help, offline | §5 Branding, §8.4 | P1 | pending |
| P7 | Notifications: inbox page `/app/notifications`, desktop bell popover, Web Push UX (contextual prompt, iOS add-to-Home-Screen guide, deep links, per-type prefs) | §7 | P1 + **Notifications Plan A merged** | pending |
| P8 | Final sweep: zero `@mui`/`@emotion`/`sx=`; full `tsc`, vitest, e2e, `next build`, GitLab CI green; coverage ≥ `main`; update `CLAUDE.md` + `plans/project_plan.md`; merge to `main`, minor version bump | §8.6, §9 | P1–P7 | pending |

**Parallel track (backend, existing plans):** Notifications Plan A → Plan B
(`docs/superpowers/plans/2026-05-02-notifications-plan-{a-foundation,b-smart-delivery}.md`).
Plan C's frontend half is superseded by P7; its backend half (webhooks, plugin channels) stays.

**After the overhaul (separate brainstorm each, in order):**
1. Phase 2 leftovers: polls UI, kudos, bookmarks, birthday reminders, nudges, collaborative lists,
   moderation UI, data-retention UI (`plans/phases/phase-2-community/`).
2. Phase 6 list templates (`plans/phases/phase-6-list-templates/`).
3. Phases 3 (intelligence) and 4 (scale) — on hold.
