# Wave 1 — Habits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feature flags + user timezone, On this day, daily question, time capsules, weekly recap email.

**Architecture:** Task 1 lands first (flags + timezone are used by all others). Tasks 2–4 run in parallel after it. Task 5 (recap) consumes 2–4 and runs last. Task 6 is the polish pass.

**Spec:** `00-overview.md` → Decisions. Global Constraints and Review Focus there apply to every task.

**Branch:** `feat/eng-w1-habits` from `feat/tags-lists-events-chats`. Worktree `/home/user/code/nexara-home`.

New notification types go in `backend/app/services/notifications/types/<key>.py`, modeled on `kudos_received.py` (register a `NotificationType`), plus a `PREF_MAP` entry.

---

### Task 1: Feature flags, user timezone, community currency

**Files:**
- Create: `backend/alembic/versions/0050_features_tz.py`, `backend/app/core/features.py`, `backend/app/api/v1/features.py`, `frontend/lib/api/features.ts`, `frontend/hooks/useFeature.ts`, `frontend/components/admin/FeaturesTab.tsx`, `frontend/components/settings/TimezoneSync.tsx`
- Modify: `backend/app/models/community.py`, `backend/app/models/user.py`, `backend/app/repositories/community_repo.py`, `backend/app/main.py` (router), `backend/app/tasks/notification_tasks.py:271` + `services/notifications/dnd.py` (use `user.timezone`), `frontend/lib/adminNav.ts`, `frontend/components/settings/ProfileTab.tsx` (timezone select), app shell (mount `TimezoneSync`)
- Test: `backend/tests/unit/core/test_features.py`, `backend/tests/unit/api/test_features_api.py`, `frontend/tests/unit/hooks/useFeature.test.tsx`, `frontend/tests/unit/components/admin/FeaturesTab.test.tsx`

**Interfaces:**
- Produces:
  - `FEATURE_DEFAULTS: dict[str, bool]` keys: `recap, on_this_day, daily_question, time_capsules, event_albums, recipes, memorials, expenses, rides, chores, relations, family_tree, reconnect_nudges, safe_arrival, voice_stories, simple_mode, newsletter, reply_by_email` — all `True` except `reply_by_email: False`.
  - `is_enabled(community: Community, key: str) -> bool` and `require_feature(community: Community, key: str) -> None` (raises `AppError(code="FEATURE_DISABLED", status_code=404)`).
  - `GET /api/v1/features` → `{key: bool}` (any member). `GET/PUT /api/v1/admin/features` (`require_role("admin")`), PUT body `{key: bool}` partial, unknown key → 422; audit log records changed keys.
  - Columns: `communities.features JSONB NOT NULL DEFAULT '{}'`, `communities.currency TEXT NOT NULL DEFAULT 'USD'` (ISO-4217, 3 upper letters), `users.timezone TEXT NULL` (IANA). Migration copies `user_settings.dnd_timezone` into `users.timezone` where not `'UTC'`.
  - Frontend `useFeature(key: FeatureKey): boolean` (true while loading = no flicker for default-on keys; false for `reply_by_email` until loaded).

- [ ] **Step 1: Failing tests**

```python
def test_defaults_when_unset():
    c = MagicMock(spec=Community); c.features = {}
    assert is_enabled(c, "recipes") is True
    assert is_enabled(c, "reply_by_email") is False

def test_override_off():
    c = MagicMock(spec=Community); c.features = {"recipes": False}
    assert is_enabled(c, "recipes") is False
    with pytest.raises(AppError) as e: require_feature(c, "recipes")
    assert e.value.code == "FEATURE_DISABLED"

def test_unknown_key_raises_keyerror():
    with pytest.raises(KeyError): is_enabled(MagicMock(features={}), "nope")
```
API tests: member PUT → 403; admin PUT `{"recipes": false}` → 200 and GET reflects it; PUT `{"bogus": true}` → 422; PATCH `/users/me` with `timezone="Mars/Base"` → 422, `"America/Phoenix"` → 200 (validate with `zoneinfo.available_timezones()`).

- [ ] **Step 2: Run, expect FAIL** — `pytest tests/unit/core/test_features.py tests/unit/api/test_features_api.py -v`
- [ ] **Step 3: Implement** migration, model columns, `core/features.py`, routes, `community_repo.update_features(cid, patch) -> dict`, `users.timezone` on profile update schema. DND + digest read `user.timezone or "UTC"`.
- [ ] **Step 4: Frontend** — `FeaturesTab` (one switch per key, grouped by wave, labels in plain words e.g. "Weekly recap email"), admin nav entry (icon `ToggleRight`); `TimezoneSync` on app mount: if `me.timezone == null` PATCH `Intl.DateTimeFormat().resolvedOptions().timeZone`; Profile tab timezone `<select>` over `Intl.supportedValuesOf("timeZone")`. Tests: FeaturesTab toggles call PUT with single key; TimezoneSync PATCHes only when null.
- [ ] **Step 5: Run all, expect PASS; commit** `feat(core): per-community feature flags and user timezone`

---

### Task 2: On this day

**Files:**
- Create: `backend/app/services/memories_service.py`, `backend/app/api/v1/memories.py`, `backend/app/tasks/memories_tasks.py`, `backend/app/services/notifications/types/on_this_day.py`, `frontend/lib/api/memories.ts`, `frontend/components/home/tiles/OnThisDayTile.tsx`
- Modify: `backend/app/repositories/post_repo.py` (new method; split to `post_memories_repo.py` if file passes 400 lines), `backend/app/tasks/celery_app.py` (beat), Home bento (add tile)
- Test: `backend/tests/integration/repositories/test_post_memories.py` (real DB), `backend/tests/unit/services/test_memories_service.py`, `frontend/tests/unit/components/home/OnThisDayTile.test.tsx`

**Interfaces:**
- Consumes: `users.timezone`, `require_feature(c, "on_this_day")`.
- Produces:
  - `PostRepository.on_this_day(community_id, viewer_id, month: int, day: int, before_year: int, limit: int = 12) -> list[dict]` — same visibility + block clauses as `list_feed`, `deleted_at IS NULL`, ordered newest year first; returns feed-shaped dicts (reuse `enrich_posts`).
  - `memory_day(today: date) -> list[tuple[int,int]]` — `[(m,d)]`, plus `(2,29)` when today is Feb 28 of a non-leap year.
  - `MemoriesService.on_this_day(viewer_id) -> list[PostResponse]` (local "today" from viewer timezone).
  - `GET /api/v1/memories/on-this-day` → `{"items": [...], "years_ago": [int]}`.
  - Beat `memories.notify_on_this_day` hourly at :05 → for users whose local hour == 9 and who have ≥1 memory and no `on_this_day` notification in the last 20 h: notify type `on_this_day` payload `{count, link:"/app?memories=1"}`.

- [ ] **Step 1: Failing tests**
  - repo: post from 2025-11-22 by Ruth (community) visible to Maya on 2026-11-22; post from 2026-11-22 excluded (current year); post in private group Maya left → excluded; post by user Maya blocked → excluded; soft-deleted → excluded.
  - `memory_day(date(2027,2,28)) == [(2,28),(2,29)]`; `memory_day(date(2028,2,28)) == [(2,28)]`.
  - service: viewer tz `Pacific/Honolulu` at 2026-11-23T05:00Z → local date 2026-11-22.
  - task: running `notify_on_this_day` twice in same hour → `notify` awaited once.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement** repo query (`extract('month'/'day', created_at AT TIME ZONE viewer_tz)`), service, route, notif type (`category="social"`, icon `history`, inapp on, email/push off), beat entry routed to `default`.
- [ ] **Step 4: Tile** — renders only when `items.length > 0`; heading "On this day"; groups by "1 year ago / 3 years ago"; each item links to `/app/post/<id>`; photos as thumbnails. Test: empty response renders nothing; two years render two groups.
- [ ] **Step 5: PASS; commit** `feat(memories): on this day tile and daily reminder`

---

### Task 3: Daily question

**Files:**
- Create: `backend/alembic/versions/0051_daily_questions.py`, `backend/app/models/question_bank.py`, `backend/app/repositories/question_bank_repo.py`, `backend/app/services/daily_question_service.py`, `backend/app/api/v1/daily_questions.py`, `backend/data/daily_questions.json` (200 entries, family-friendly, no duplicates), `frontend/components/prompts/DailyQuestionCard.tsx`, `frontend/components/admin/QuestionBankSection.tsx`
- Modify: `backend/app/models/prompt.py` (+`reveal_after_answer`), `backend/app/services/prompt_service.py` (`should_fire` "daily"; `fire_due_prompts` pulls text from bank for `prompt_type="daily_question"`; `list_responses` gating), `frontend/components/admin/PromptsTab.tsx` (mount bank section), Home feed top slot
- Test: `backend/tests/unit/services/test_daily_question_service.py`, `backend/tests/unit/services/test_prompt_service.py` (extend), `frontend/tests/unit/components/prompts/DailyQuestionCard.test.tsx`

**Interfaces:**
- Consumes: `require_feature(c, "daily_question")`.
- Produces:
  - Table `question_bank(id uuid pk, community_id, text text ≤280, source text check in ('builtin','admin','member'), status text check in ('approved','pending','rejected'), suggested_by uuid null, used_at timestamptz null, created_at)`; seed builtin rows per community lazily on first fire.
  - `prompts.reveal_after_answer bool NOT NULL DEFAULT false`. Migration inserts, per community, one prompt `prompt_type='daily_question', frequency_type='daily', reveal_after_answer=true, scope='community'`.
  - `should_fire`: `ftype == "daily"` → `True`.
  - `QuestionBankRepository.next_question(cid) -> QuestionBank | None` — approved, `used_at IS NULL`, order: `source != 'builtin'` first, then `created_at`, then random for builtin; when all used, reset builtin `used_at` to NULL and retry once.
  - `PromptService.list_responses` returns `{"locked": True, "count": n, "items": []}` when `prompt.reveal_after_answer` and viewer has no response post and viewer isn't the prompt creator.
  - Group daily question: group admins create a prompt with `prompt_type='daily_question', scope='subgroup'` via existing `POST /prompts` (allow this type for group admins); it draws from the same community bank but tracks its own `used_at` per prompt via `question_bank_uses(prompt_id, question_id)` (in 0051) instead of `question_bank.used_at` when scope is subgroup.
  - Routes: `POST /daily-questions/suggest {text}` (member → pending; rate 3/day/user), `GET /admin/daily-questions?status=pending`, `POST /admin/daily-questions/{id}/approve|reject`, `POST /admin/daily-questions {text}` (approved).
- [ ] **Step 1: Failing tests**
  - `should_fire(daily prompt, any date)` is True; disabled → False.
  - next_question prefers admin/member approved over builtin; skips pending/rejected; exhaust → recycles builtin.
  - firing twice same day → one PromptPost (existing idempotency must hold — assert).
  - gating: viewer without answer → locked with count 2; after answering → items length 3; creator sees items.
  - suggest 4th in a day → 429 `RATE_LIMITED`.
- [ ] **Step 2: FAIL** → **Step 3: implement** → **Step 4: Frontend**: card shows question, "Answer to see what everyone said" + count when locked; answer composer inline; after posting, query invalidates and answers render. Admin section: pending list with Approve/Reject, add-question input. Tests: locked state shows count text, not answers.
- [ ] **Step 5: PASS; commit** `feat(prompts): daily question with answer-to-reveal`

---

### Task 4: Time capsules

**Files:**
- Create: `backend/alembic/versions/0052_time_capsules.py`, `backend/app/models/time_capsule.py`, `backend/app/repositories/time_capsule_repo.py`, `backend/app/schemas/time_capsule.py`, `backend/app/services/time_capsule_service.py`, `backend/app/api/v1/time_capsules.py`, `backend/app/tasks/capsule_tasks.py`, `backend/app/services/notifications/types/capsule_opened.py`, `frontend/lib/api/capsules.ts`, `frontend/app/app/capsules/page.tsx`, `frontend/app/app/capsules/[id]/page.tsx`, `frontend/components/capsules/{CapsuleComposer,SealedCard,CapsuleView}.tsx`
- Modify: composer toolbar (Hourglass button → `CapsuleComposer`), `backend/app/services/media_service.py` (sealed media guard), nav "More" entry
- Test: `backend/tests/unit/services/test_time_capsule_service.py`, `backend/tests/integration/api/test_capsule_media_guard.py`, `frontend/tests/unit/components/capsules/*.test.tsx`

**Interfaces:**
- Produces:
  - Tables: `time_capsules(id, community_id, author_id, title text ≤120, body text, media_ids uuid[] default '{}', open_at timestamptz, opened_at null, created_at, deleted_at)`; `time_capsule_recipients(capsule_id fk cascade, kind text check in ('user','subgroup','community','household'), target_id uuid null, PRIMARY KEY(capsule_id, kind, target_id))`.
  - `CapsuleCreate{title, body, media_ids ≤10, open_at, recipients:[{kind,target_id}] ≥1}`; `CapsuleSealed{id,title,author,open_at,recipients_summary}`; `CapsuleOpen(CapsuleSealed){body, media}`.
  - Rules: `open_at` ≥ now+24h and ≤ now+50y; recipients must be visible to author (user not blocked, subgroup member, household visible); media must be author's own.
  - Service: `create`, `list_for_viewer(viewer_id) -> {"sealed":[CapsuleSealed], "opened":[CapsuleOpen], "mine":[...]}`, `get(id, viewer_id)` (returns Open only if `opened_at` set or viewer is author), `delete(id, actor_id)` (author only), `open_due(now) -> int`.
  - Viewer is a recipient if: `user` target = viewer; `subgroup` member; `community`; `household` member owner = viewer.
  - `MediaService` serve/thumbnail: media id referenced by an unopened capsule is 404 for everyone but the author.
  - Beat `capsules.open_due` every 10 min: set `opened_at`, notify each resolved recipient once (`capsule_opened`, payload `{capsule_id, title, author_name, link}`), skip blocked pairs.
  - No PATCH route (sealed = immutable).
- [ ] **Step 1: Failing tests**
  - open_at 2 hours out → 422; 51 years → 422.
  - recipient Maya GET before open → sealed fields only; `body` key absent from JSON.
  - author GET before open → body present.
  - non-recipient GET → 404.
  - media URL of sealed capsule as Maya → 404; after open → 200.
  - `open_due` twice → each recipient notified once; household recipient → owner notified.
  - capsule text never appears in `/search?q=` results (search does not index capsules — assert no hit).
- [ ] **Step 2: FAIL** → **Step 3: implement** → **Step 4: Frontend**: composer (title, message, photos, open date `<input type="date">`, recipients picker reusing ship-to person picker + group + household lists), sealed card ("Opens May 1, 2034 · from Ruth", lock icon, no blur-teaser of content), opened view, page tabs Sealed / Opened / Sent by me. Tests: sealed card has no body text; composer blocks date < tomorrow.
- [ ] **Step 5: PASS; commit** `feat(capsules): sealed time capsules with scheduled opening`

---

### Task 5: Weekly recap email

**Files:**
- Create: `backend/alembic/versions/0053_recap_settings.py`, `backend/app/services/recap_service.py`, `backend/app/services/recap_sections.py`, `backend/app/tasks/recap_tasks.py`, `backend/app/api/v1/recap.py` (unsubscribe), `backend/templates/email/recap.html`, `frontend/components/settings/RecapSetting.tsx`
- Modify: `backend/app/models/user_settings.py` (+`recap_cadence`, `recap_last_sent_at`), settings schemas, `celery_app.py` (beat), notifications settings tab
- Test: `backend/tests/unit/services/test_recap_service.py`, `backend/tests/unit/tasks/test_recap_tasks.py`, `backend/tests/unit/api/test_recap_unsubscribe.py`

**Interfaces:**
- Consumes: `MemoriesService.on_this_day`, `PromptService` (yesterday's daily prompt post + `response_count`), `CelebrationService.occurrences`/range for next 7 days, `TimeCapsuleService.list_for_viewer` (opened in last 7 days), `users.timezone`, `is_enabled`.
- Produces:
  - `user_settings.recap_cadence text NOT NULL DEFAULT 'weekly' check in ('weekly','monthly','off')`, `recap_last_sent_at timestamptz null`.
  - `RecapSection = TypedDict{key: str, title: str, items: list[dict]}`; `recap_sections.SECTIONS: list[Callable[[RecapContext], Awaitable[RecapSection | None]]]` — later waves append (albums, recipes, story requests, chores). ponytail: plain list, no registry class.
  - `recap_due(cadence, local_now: datetime, last_sent: datetime | None) -> bool` — weekly: Sunday and hour == 8 and (last None or ≥6 days ago); monthly: day 1 and hour 8 and (last None or ≥27 days).
  - `RecapService.build(user) -> list[RecapSection]` (empty sections dropped; skip email when list empty).
  - Beat `recap.dispatch` hourly at :10 → `send_recap_email.delay(user_id)` for due users with email + feature on; stamp `recap_last_sent_at` before enqueue (idempotent).
  - Unsubscribe: `GET /api/v1/recap/unsubscribe?token=` — token = existing signed-token helper (same one used by magic links) with purpose `recap_unsub`, 90-day TTL; sets cadence `off`; returns small HTML page. Email has `List-Unsubscribe` header.
- [ ] **Step 1: Failing tests**
  - `recap_due("weekly", Sun 08:30 local, None)` True; Sat → False; Sun 08 with last 2 days ago → False; `"off"` → False.
  - user in `Pacific/Honolulu`: UTC Sunday 18:10 → due; UTC Sunday 08:10 → not.
  - build with no data → `[]` and no email sent.
  - dispatch twice same hour → one `send_recap_email.delay`.
  - section content excludes posts the user can't see (reuse memories repo — assert blocked author absent).
  - unsubscribe bad token → 400; good → cadence `off`.
- [ ] **Step 2: FAIL** → **Step 3: implement** (template extends `base.html`, one heading per section, plain links, alt text, 600px single column) → **Step 4: Settings UI**: radio Weekly / Monthly / Off under Notifications ("Family recap email"). Test: selecting Off PATCHes `recap_cadence`.
- [ ] **Step 5: PASS; commit** `feat(recap): weekly family recap email`

---

### Task 6: Wave polish + PR (orchestrator)

- [ ] Migrate local DBs `nexara` and `nexara_test` to 0053 (`alembic upgrade head` with each URL).
- [ ] Full suites: `pytest -q` (expect only the 9 known pre-existing failures), `npm test`, lint/type/format both sides.
- [ ] Rebuild eval stack (`git merge` branch into build dir, `docker compose -p nexara-eval up -d --build nexara`); as Ruth + Maya verify: flag off hides recipes nav/API 404; On this day tile shows seeded 2025 post; daily question locked→unlocked; capsule sealed for Maya, author sees body, force `open_at` in DB → `open_due` → Maya notified; trigger `recap.dispatch` with mocked clock → email in mail log.
- [ ] Screenshots light/dark + phone width; fix copy, focus rings, empty states; `/simplify` on wave diff.
- [ ] Push to `github`, open PR "feat: engagement wave 1 — habits" based on #385; body lists features, migrations 0050–0053, test results.
