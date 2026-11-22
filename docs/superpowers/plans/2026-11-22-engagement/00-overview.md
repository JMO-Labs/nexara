# Engagement Phase — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give families reasons to come back and things to build together: recap email, memories, daily question, capsules, albums, recipes, memorials, expenses, rides, chores, relations + family tree, reconnect nudges, safe-arrival, voice stories, simple mode, printable newsletter, reply-by-email.

**Architecture:** Five waves, each a stacked PR chain on `feat/tags-lists-events-chats` (#385). Every feature sits behind a per-community feature flag (wave 1 task 1). Reuse existing systems first: prompts (daily question), galleries (albums), nudges (reconnect), digest email plumbing (recap), household members (memorials, tree nodes), list assignments (chores).

**Tech Stack:** FastAPI, async SQLAlchemy 2, Alembic, Celery beat, Postgres 16, Next 16 / React 19, TanStack Query, Tailwind v4, Vitest, pytest.

**Spec:** grilling decisions Q1–Q36, recorded in the section "Decisions" below (no separate spec doc).

## Files

| File | Wave | PR branch |
|---|---|---|
| `01-wave-habits.md` | 1: flags+tz, On this day, daily question, time capsules, recap email | `feat/eng-w1-habits` |
| `02-wave-content.md` | 2: event albums+slideshow, recipes, memorials | `feat/eng-w2-content` |
| `03-wave-practical.md` | 3: expenses, rides, chore rotation | `feat/eng-w3-practical` |
| `04-wave-connection.md` | 4: relations, family/group tree, reconnect nudges, safe arrival, voice stories | `feat/eng-w4-connection` |
| `05-wave-access.md` | 5: simple mode, newsletter, reply-by-email | `feat/eng-w5-access` |

Each wave branch starts from the previous wave's branch. Each wave ends with a **polish task** (live verify on eval stack, a11y, copy, screenshots, full suites) before its PR opens.

## Decisions (spec)

- Q1 order = waves above. Q2/Q22 per-community flags in one `communities.features` JSONB + admin "Features" tab; all on by default except `reply_by_email` (off).
- **Kid accounts dropped** (user: "need auth"). Kids use normal accounts.
- Q3/Q32 Recap email: weekly Sun 08:00 user-local, default on, cadence weekly|monthly|off, unsubscribe link, skip when empty. Sections: On this day, yesterday's question + answer count, birthdays next 7 days, capsules opened, new albums, new recipes, pending story requests, my chores.
- Q4 On this day: posts/photos from same month/day in past years the viewer can see now; Home tile (hidden when empty), recap section, ≤1 notification/day.
- Q5/Q28 Daily question: bank of ~200 built-in + admin + approved member suggestions; one per day; answers hidden until viewer answers; community-wide, groups may run their own; voice answers once wave 4 ships.
- Q6 Time capsule: sealed card (title, author, open date) to recipients; body/media hidden server-side until open; no edit after seal; author may delete; recipients = user | group | community | household member (owner receives); notify on open. Author can read own capsule (decision made in plan — flag on review if not wanted).
- Q7 Reconnect nudges: private; confirmed family relations (not friends) with no DM/comment/kudos in N days (default 30); ≤1/week; snooze person; off switch.
- Q8/Q30 Safe arrival: trip label + expected time + chosen watchers; "Made it" tap; one overdue alert at expected+1h; trip auto-ends expected+24h; traveler can extend; watchers get "made it" (mutable).
- Q9/Q26 Memorials: household member `passed_on` date; account memorial = `users.memorialized_at` (admin only; locks login, removed from mentions/nudges/pickers; birthday → "Remembering" day). Creators: admin or confirmed relative.
- Q10/Q29 Expenses: tracking only; ledger (named, members, optional event/wishlist link, currency default from community setting); equal or custom split; balances; simplified debts; mark settled.
- Q11 Simple mode: per-user + admin can set; ~125% text, nav = feed, photos, family, calendar; big targets; no hover-only controls.
- Q13/Q31 Newsletter: browser print page `/app/newsletter/YYYY-MM`; auto-curated (top-reacted posts/photos, birthdays, milestones, recipes, opened capsules, events + places); admin pin/hide; viewer-visible only. No server PDF.
- Q14 Recipes: own tables; linked from list items.
- Q15/Q23/Q36 Relations: store parent, child, spouse, partner, sibling, friend, other; derive grandparent/aunt/cousin labels; request→confirm; either side removes; "relations" uses per-field visibility, default community; household members linkable.
- Q16 `users.timezone` (browser-detected when unset, editable); DND uses it.
- Q17 Audio: m4a/mp3/ogg/opus/webm, ≤15 min, ≤25 MB, transcode to m4a; no transcription.
- Q18 Albums: auto-create event gallery, "share your photos" reminder day after, TV slideshow.
- Q19 Rides: own tables, offer/request, seats, origin, depart time, on event page, driver notified.
- Q20 Chores: repeat daily|weekly|monthly + rotation order; missed → advance + mark missed.
- Q21 Reply by email: IMAP polling + `reply+<token>@domain`; off by default; admin settings; strip quotes/signatures; token-bound to user+post+expiry.
- Q24/Q25/Q35 Tree: users + household persons + memorials; hidden → "Private relative"; own SVG generational layout, pan/zoom, >300 nodes → nearby generations + expand; group Tree tab = members only, family clusters, friend dashed, unlinked listed, outsider-mediated link shown as "related via family".
- Q27 Story requests: ask a member a question; 30-day expiry, one reminder, silent decline; Stories tab on profile; built-in story-question bank.
- Q33 stack on #385, migrations continue at 0050. Q34 subagents per task, orchestrator reviews + live-tests + polishes per wave.

## Migration numbers (fixed — parallel tasks must use exactly these)

| Rev | Wave.Task | down_revision |
|---|---|---|
| 0050_features_tz | 1.1 | 0049_tag_targets |
| 0051_daily_questions | 1.3 | 0050_features_tz |
| 0052_time_capsules | 1.4 | 0051_daily_questions |
| 0053_recap_settings | 1.5 | 0052_time_capsules |
| 0054_album_reminder | 2.1 | 0053_recap_settings |
| 0055_recipes | 2.2 | 0054_album_reminder |
| 0056_memorials | 2.3 | 0055_recipes |
| 0057_expenses | 3.1 | 0056_memorials |
| 0058_event_rides | 3.2 | 0057_expenses |
| 0059_chore_rotation | 3.3 | 0058_event_rides |
| 0060_relations | 4.1 | 0059_chore_rotation |
| 0061_reconnect | 4.3 | 0060_relations |
| 0062_trips | 4.4 | 0061_reconnect |
| 0063_stories | 4.5 | 0062_trips |
| 0064_simple_mode | 5.1 | 0063_stories |
| 0065_newsletter | 5.2 | 0064_simple_mode |
| 0066_reply_email | 5.3 | 0065_newsletter |

Revision id = the filename stem (e.g. `revision = "0050_features_tz"`). Check the exact id string of 0049 with `alembic heads` before writing 0050.

## Global Constraints

- Layering: `api/v1/*` → `services/*` → `repositories/*`; routes never import repos; every query filters `community_id`; viewer reads use block filter (`not_blocked` / `apply_block_filter`).
- Errors only via `core/exceptions.py`; new notif types added to `PREF_MAP` (`services/notification_service.py:59`) with in-app default on.
- Every feature checks `require_feature(community, "<key>")` (wave 1.1) in its service entry points; frontend hides UI when `useFeature(key)` is false.
- Files ≤ 400 lines; Doxygen `@file/@brief/@param/@return` headers.
- Migrations: exact numbers above; downgrade must fully reverse.
- UI: WCAG 2.1 AA, keyboard reachable, visible focus, `prefers-reduced-motion` honored, theme tokens only (no raw hex), sentence-case copy, no all-caps labels.
- Times stored UTC (`timestamptz`); user-local logic uses `users.timezone` (fallback `UTC`).
- Before every commit: `ruff check . && ruff format --check . && mypy app/` (backend), `npx eslint . && npx prettier --check . && npx tsc --noEmit` (frontend), plus the task's tests. Conventional commits, ≤72-char subject, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: backend unit idiom `AsyncMock(spec=Repo)` + `MagicMock(spec=Model)`; repo tests use real Postgres `nexara_test`. Never run `alembic upgrade` against `nexara_test` from a subagent — orchestrator migrates shared DBs.
- No new dependencies except where a task names one (none planned; IMAP/email parsing use stdlib).
- Push only to remote `github`; never force-push.

## Review Focus (cross-wave)

1. **Visibility leaks through aggregates** — On this day, recap, newsletter, tree must never include content the viewer can't open now (deleted, blocked author, private group they left). Each owning task has a test.
2. **Timezone edges** — user in UTC−10 on Sunday 08:00 local is Sunday 18:00 UTC; Feb 29 memories in non-leap years show on Feb 28. Tests in 1.2 and 1.5.
3. **Double-fire of beat jobs** — every periodic job is idempotent via a stamp column (`*_sent_at`, `opened_at`, `alerted_at`, `reminded_at`); tests call the job twice and assert one notification.
4. **Sealed content via side channels** — capsule body/media must not leak through search, media URLs, notifications, or feed before `open_at`. Test in 1.4.
5. **Money rounding** — equal split of 1000¢ among 3 = 334/333/333 summing exactly; settlement simplification preserves net balances. Test in 3.1.
