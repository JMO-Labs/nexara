# PR 7 — Onboarding, age groups, NSFW

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** New members set up their profile; admins manage age groups; NSFW content never reaches children/teens.
**Spec:** `00-overview.md` (Q15–Q18). **Branch:** `feat/plat-7-onboard` from `feat/plat-6-monitor`. Task 1 → (2 ∥ 3 ∥ 4) → 5.

---

### Task 1: Age groups backend

**Files:**
- Create: `backend/alembic/versions/0074_onboarding_age.py`, `backend/app/services/age_service.py`, `backend/app/models/age_suggestion.py`, `backend/app/repositories/age_repo.py`, `backend/app/api/v1/age_groups.py`
- Modify: `backend/app/models/user.py`, `backend/app/models/invite.py`, `backend/app/models/community.py`, `backend/app/services/search_service.py` (`is_adult` → `age_service.is_adult`)
- Test: `backend/tests/unit/services/test_age_service.py`, `backend/tests/integration/api/test_age_groups.py`

**Interfaces:**
- Columns: `users.age_group text null check in ('child','teen','adult')` (admin-set), `invites.age_group` same; `communities.adult_requires_approval bool default false`; `communities.onboarding_required text[] default '{}'`; `users.onboarding_step int default 0`, `users.onboarding_done_at timestamptz` (existing users backfilled `now()`); table `age_suggestions(id, community_id, subject_id, suggested_by, age_group, note text ≤500, status 'pending'|'approved'|'rejected', decided_by, decided_at, created_at)`, unique pending per (subject, suggested_by).
- `def effective_age_group(user, community) -> Literal['child','teen','adult','unknown']`: admin-set wins; else birthday (<13 child, <18 teen, else adult — but if `adult_requires_approval` birthday-adult → `unknown`); else `unknown`.
- `def is_adult(user, community) -> bool` = effective == 'adult'.
- API: `POST /api/v1/age-groups/suggestions {subject_id, age_group, note}` (any member, not self); `GET /api/v1/admin/age-groups/suggestions?status=pending`; `POST .../{id}/approve|reject`; `PUT /api/v1/admin/users/{id}/age-group {age_group|null}`; `PUT /api/v1/admin/age-groups/settings {adult_requires_approval}`; `GET /api/v1/users/me` includes `age_group` (effective, read-only). Audit `age_group.set`, `age_group.suggestion.approved|rejected`. Subject never notified; admins get in-app `age_suggestion` notification (PREF_MAP).
- Invite accept copies `invites.age_group` to user.
- [ ] Tests: birthday 15 y → teen; admin set adult overrides birthday 10 y; approval mode + birthday 30 y + unset → `unknown` (not adult); suggest self → 400; approve sets user's group + audit row; member can't approve (403).
- [ ] Implement → PASS → commit `feat(users): age groups with admin control and member suggestions`

---

### Task 2: NSFW gating backend

**Files:**
- Modify: `backend/app/repositories/visibility_preds.py` (+`nsfw_allowed(viewer_adult: bool)`), every post/media read path that uses `post_visible` (feed, group posts, profile posts, post detail, comments list, galleries/media, memories/On this day, newsletter, search), notification fan-out (`notification_service` skip non-adult recipients for NSFW targets), `backend/app/models/gallery.py` (`is_nsfw` on albums; media in NSFW album inherits), post/media/gallery create+update schemas (`is_nsfw`), moderation (flag/unflag endpoint `PUT /api/v1/moderation/posts/{id}/nsfw {value}` audit), user settings `always_show_nsfw bool default false`, features flag `nsfw` (default on; off → toggle hidden in UI, already-flagged content stays hidden from non-adults)
- Test: `backend/tests/integration/repositories/test_nsfw_gating.py`

**Interfaces:**
- `post_visible(viewer)` gains `nsfw_allowed` clause: `Post.is_nsfw.is_(False) | literal(viewer_adult)`; viewer_adult computed once per request via `age_service.is_adult` and passed through the existing predicate builder.
- Post detail / media URL for hidden NSFW → 404 (same as not visible).
- [ ] Review-focus test: teen views NSFW post by id → 404; its comments list → 404; feed/search/profile/group/newsletter/On this day omit it; comment on NSFW post notifies only adult recipients; media in NSFW album → 404 for teen, 200 for adult; unknown-age user treated as teen.
- [ ] Implement → PASS → commit `feat(safety): hide NSFW posts and media from non-adults everywhere`

---

### Task 3: NSFW UI

**Files:**
- Create: `frontend/components/feed/NsfwCover.tsx`, `frontend/components/compose/NsfwToggle.tsx`
- Modify: post composer, photo upload dialog, album create/edit, PostCard + media tiles (wrap with cover), moderation menu ("Mark NSFW" / "Remove NSFW"), Settings › Privacy (`always_show_nsfw` "Always show NSFW content"; only shown to adults)
- Test: `frontend/tests/unit/feed/NsfwCover.test.tsx`
- Label exact: toggle "NSFW", help "Hidden from children and teens. Adults see it blurred until they tap."; cover button "NSFW — tap to view" (`aria-label="Show NSFW content"`), blur `backdrop-filter`-free (`filter: blur(24px)` on content, cover has solid `--nx-glass-solid`). Toggle hidden for non-adults and when feature off.
- [ ] Tests: cover hides content until click; `always_show_nsfw` renders without cover; teen composer has no toggle.
- [ ] Implement → PASS → commit `feat(ui): NSFW toggle and blur cover`

---

### Task 4: Admin age-group UI + suggest action

**Files:**
- Create: `frontend/components/admin/AgeGroupsTab.tsx` (pending queue approve/reject with note, setting switch), `frontend/components/profile/SuggestAgeGroupDialog.tsx`
- Modify: `frontend/components/admin/UsersTab.tsx` (Age group column + select), `frontend/components/admin/InvitesTab.tsx` (age group select), profile "…" menu ("Suggest age group"), Settings › Account (read-only "Age group: Teen — set by your admin")
- Test: frontend tests for tab + dialog
- [ ] Tests: approve calls endpoint and removes row; suggest dialog posts `{subject_id, age_group, note}`; own profile has no suggest action.
- [ ] Implement → PASS → commit `feat(admin): age group management and member suggestions`

---

### Task 5: Onboarding wizard

**Files:**
- Create: `frontend/app/app/welcome/page.tsx`, `frontend/components/onboarding/steps/{ProfileStep,BirthdayStep,ContactStep,FamilyStep,NotifyStep,SecurityStep}.tsx`, `frontend/components/onboarding/OnboardingGate.tsx`, `frontend/components/home/CompleteProfileCard.tsx`, `backend/app/api/v1/onboarding.py`, `frontend/components/admin/OnboardingSettings.tsx`
- Modify: `frontend/components/layout/Shell.tsx` (gate), `WelcomeModal`/`OnboardingTour` start after `onboarding_done_at`
- Test: `backend/tests/integration/api/test_onboarding.py`, `frontend/tests/unit/onboarding/*.test.tsx`

**Interfaces:**
- API: `GET /api/v1/onboarding` → `{step, done, required: string[], steps: ['profile','birthday','contact','family','notify','security'], prefill:{display_name, avatar_url, email}}` (prefill from SSO claims stored at provisioning); `PUT /api/v1/onboarding {step}`; `POST /api/v1/onboarding/complete` → 400 `onboarding_incomplete` listing missing required fields; admin `PUT /api/v1/admin/onboarding {required}`.
- `security` step is required automatically when the PR 3 policy covers the user.
- Gate: if `!done` and path not `/app/welcome` → `router.replace('/app/welcome')`. Steps reuse existing editors (AvatarPicker, ProfileDetailsPanel fields, VisibilitySelect default "Only me", AddRelationDialog, HouseholdPanel, PushDevices, TotpSetup/PasskeyList). Each step: "Continue", "Skip for now" (absent when required), progress "Step 2 of 6", Back.
- Existing users (backfilled done) see `CompleteProfileCard` on Home when profile lacks avatar/birthday/relations; dismiss stored in user settings `profile_card_dismissed`.
- [ ] Tests: new user hitting `/app` redirected to `/app/welcome`; required `birthday` blocks complete; skip advances step and persists; resume returns to saved step; SSO prefill shows name.
- [ ] Implement → PASS → commit `feat(onboarding): guided profile setup for new members`

---

### Task 6: Phase polish
- [ ] Full suites + build; live script: invite teen (age preset) → onboarding → can't see NSFW post; adult sees cover; suggestion approve flow; screenshots phone + desktop of each onboarding step; PR "Platform 7: onboarding, age groups, NSFW"; update memory file with phase status.
