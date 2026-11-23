# PR 8 — Countdowns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Members create countdowns ("12 days until Dad's retirement") others follow; shown in feed and a fixed Home strip, with reminders.
**Spec:** `00-overview.md` (Q20–Q23). **Branch:** `feat/plat-8-countdowns` from `feat/plat-7-onboard`. Task 1 → (2 ∥ 3) → 4.

---

### Task 1: Backend

**Files:**
- Create: `backend/alembic/versions/0075_countdowns.py`, `backend/app/models/countdown.py`, `backend/app/repositories/countdown_repo.py`, `backend/app/services/countdown_service.py`, `backend/app/api/v1/countdowns.py`, `backend/app/schemas/countdown.py`, `backend/app/tasks/countdown_tasks.py`
- Modify: `router.py`, notification registry + `PREF_MAP` (`countdown_reminder`, in-app + push default on, email off), `celery_app.py` beat (`countdown-reminders` hourly, `notifications` queue), feed (`post_repo.list_feed` — countdown posts via existing post pipeline)
- Test: `backend/tests/unit/services/test_countdown_service.py`, `backend/tests/integration/api/test_countdowns.py`

**Interfaces:**
- Tables: `countdowns(id, community_id, author_id, title text ≤120, target_date date, target_time time null, tz text, emoji text ≤8 null, cover_media_id uuid null, repeat_yearly bool default false, visibility text check in ('community','subgroup','private'), subgroup_id null, post_id uuid null, created_at, deleted_at)`; `countdown_followers(countdown_id, user_id, created_at, pk(countdown_id,user_id))`; `countdown_reminders_sent(countdown_id, user_id, kind text check in ('d7','d1','d0'), occurrence date, pk(all four))`.
- Visibility reuses the post visibility predicate rules (community / subgroup member / author only) plus `not_blocked` and NSFW-agnostic (no NSFW flag).
- `next_occurrence(c, today) -> date`: target_date; if `repeat_yearly` and past → same month/day next year (Feb 29 → Feb 28).
- `days_left(c, viewer_today) -> int` (0 = today).
- Create: inserts countdown + a feed `Post` with `kind='countdown'` and `countdown_id` (add nullable `posts.countdown_id` FK) using the countdown's visibility; author auto-follows.
- API: `POST /api/v1/countdowns`, `GET /api/v1/countdowns/{id}`, `PATCH`, `DELETE` (author or admin; deletes post too), `POST|DELETE /api/v1/countdowns/{id}/follow`, `GET /api/v1/countdowns/following?include_done=false` (for Home: followed, sorted by days_left, hides non-yearly ones >3 days past), `GET /api/v1/countdowns?scope=all` (browse visible). Response includes `days_left`, `next_date`, `following`, `follower_count`.
- Reminder task: for each follower (viewer tz from `users.timezone`), when days_left ∈ {7,1,0} for current occurrence and no `countdown_reminders_sent` row → notify `countdown_reminder` ("7 days until Dad's retirement" / "Tomorrow: …" / "Today: Dad's retirement!") with link `/app/countdowns/{id}`; insert row (idempotent).
- [ ] Tests: yearly Feb 29 → Feb 28 next year; private countdown 404 for others; subgroup only for members; follow requires visibility; reminder sent once per kind per occurrence; deleting countdown removes feed post; Home list hides 4-days-past one-off but keeps yearly (rolled).
- [ ] Implement → PASS → commit `feat(countdowns): scoped countdowns with follow and reminders`

---

### Task 2: Create + feed card + page

**Files:**
- Create: `frontend/lib/api/countdowns.ts`, `frontend/hooks/useCountdowns.ts`, `frontend/components/countdowns/{CountdownCard,CountdownComposer,FollowButton}.tsx`, `frontend/app/app/countdowns/[id]/page.tsx`, `frontend/app/app/countdowns/page.tsx`
- Modify: Create menu (+"Countdown"), `PostCard` (render `CountdownCard` when `post.countdown`)
- Test: `frontend/tests/unit/countdowns/*.test.tsx`
- Card: big number + "days until" + title, emoji/cover, date line, Follow/Following toggle (`aria-pressed`), follower count; day 0 → "Today!" with confetti-free celebratory accent (respect reduced motion); singular "1 day".
- Composer: title, date (`<input type="date">`), optional time, emoji, cover upload (existing media picker), scope (existing `ScopeSelect`), "Repeats every year" switch.
- [ ] Tests: "1 day until" singular; follow toggles and updates count optimistically; composer posts payload; day 0 shows "Today!".
- [ ] Implement → PASS → commit `feat(countdowns): create, feed card, and countdown page`

---

### Task 3: Home strip + notification toggle

**Files:**
- Create: `frontend/components/home/CountdownStrip.tsx`
- Modify: Home layout (fixed area above feed; phone: horizontal scroll strip), `NotificationMatrix` label `countdown_reminder` "Countdown reminders", i18n
- Test: `frontend/tests/unit/home/CountdownStrip.test.tsx`
- Strip hidden when following none; ≤6 chips (emoji, "12d", title), "See all" → `/app/countdowns`.
- [ ] Tests: hidden when empty; sorted soonest first; 7th not shown + See all link.
- [ ] Implement → PASS → commit `feat(home): countdowns strip`

---

### Task 4: Polish PR 8
- [ ] Full suites + build; live script (create community + group + private countdowns as different users; visibility; follow; run reminder task with target 7 days out → one notification; run twice → still one); screenshots desktop + phone (feed card, Home strip, page); PR "Platform 8: countdowns".
