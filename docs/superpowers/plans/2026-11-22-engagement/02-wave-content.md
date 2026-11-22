# Wave 2 — Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Event albums with TV slideshow, family recipe book, memorials.

**Architecture:** Three independent tasks (parallel), then polish. Albums reuse `Gallery` (`is_event_gallery`, `services/event_gallery.py`). Memorials reuse `HouseholdMember` and add one user column. Recipes are new tables.

**Spec:** `00-overview.md`. **Branch:** `feat/eng-w2-content` from `feat/eng-w1-habits`.

---

### Task 1: Event albums + slideshow

**Files:**
- Create: `backend/alembic/versions/0054_album_reminder.py`, `backend/app/tasks/album_tasks.py`, `backend/app/services/notifications/types/album_reminder.py`, `frontend/components/galleries/Slideshow.tsx`, `frontend/app/app/galleries/[id]/slideshow/page.tsx`
- Modify: `backend/app/schemas/event.py` (`auto_create_gallery` default `True`), event create modal (checkbox default checked, label "Create a shared photo album"), gallery page (Slideshow button), `recap_sections.py` (+ new albums section), `celery_app.py`
- Test: `backend/tests/unit/tasks/test_album_tasks.py`, `backend/tests/unit/services/test_event_service.py` (default), `frontend/tests/unit/components/galleries/Slideshow.test.tsx`

**Interfaces:**
- Produces: `events.album_reminded_at timestamptz null`; beat `albums.remind` hourly: events with gallery whose end (or start+3h when no end) is 18–30 h ago and `album_reminded_at IS NULL` → notify RSVP "going" users (type `album_reminder`, payload `{event_id, gallery_id, title, link}`), stamp. Recap section `new_albums` (event galleries created last 7 days, visible to user, ≥1 item).
- Slideshow: props `{items: GalleryItem[], startIndex?: number}`; Fullscreen API on enter; ←/→/Space/Esc; auto-advance 6 s, pause button (`aria-pressed`); captions = item caption + uploader; preloads next image; `prefers-reduced-motion` → no crossfade; video items play muted then advance on end.
- [ ] Tests: reminder fires once for event ended 20 h ago; not for 40 h ago; not twice; skips non-going RSVPs. Slideshow: ArrowRight advances; Space toggles pause; reduced-motion class absent of transition.
- [ ] Implement → PASS → commit `feat(galleries): auto event albums, photo reminder, slideshow`

---

### Task 2: Recipe book

**Files:**
- Create: `backend/alembic/versions/0055_recipes.py`, `backend/app/models/recipe.py`, `backend/app/repositories/recipe_repo.py`, `backend/app/schemas/recipe.py`, `backend/app/services/recipe_service.py`, `backend/app/api/v1/recipes.py`, `frontend/lib/api/recipes.ts`, `frontend/app/app/recipes/{page,[id]/page,new/page}.tsx`, `frontend/components/recipes/{RecipeCard,RecipeForm,RecipeView,IngredientList}.tsx`
- Modify: `backend/app/models/list.py` (+`recipe_id` on list item), list item edit UI ("Link a recipe"), nav (icon `ChefHat`), `recap_sections.py` (+new recipes), mention sync (`MentionTagsService.sync_mentions` on `story`, target type `recipe` — add to tag target check constraint in 0055)
- Test: `backend/tests/unit/services/test_recipe_service.py`, `backend/tests/integration/repositories/test_recipe_repo.py`, `frontend/tests/unit/components/recipes/*.test.tsx`

**Interfaces:**
- Table `recipes(id, community_id, author_id, title ≤120, story text, ingredients jsonb [{qty: str, item: str}] ≤100, steps jsonb [str] ≤60, servings int null, prep_minutes int null, cook_minutes int null, photo_media_ids uuid[] ≤10, best_maker_user_id null, best_maker_household_id null, tags text[] ≤10, visibility, subgroup_id null, search_fts tsvector computed(title, story, ingredients::text), created_at, updated_at, deleted_at)`, GIN on search_fts and tags. `list_items.recipe_id uuid null fk set null`.
- Service: `create/update/delete` (author or admin), `list(viewer_id, q: str|None, tag: str|None, cursor) -> page`, `get(id, viewer_id)`; standard visibility (`community|subgroup|private`) + block filter; photos must be author's media.
- Routes `/api/v1/recipes` CRUD + `GET /recipes/tags` (distinct tags with counts).
- UI: grid of cards (photo, title, best maker); detail = story first, then ingredients (checkboxes, local only) and numbered steps; "Made best by" chip links person/household; servings scaler deferred (ponytail: not requested).
- [ ] Tests: search "cornbread" finds by ingredient; private recipe hidden from others; subgroup recipe hidden after leaving group; list item with deleted recipe → `recipe_id` null; ingredients >100 → 422; @mention in story tags user.
- [ ] Implement → PASS → commit `feat(recipes): family recipe book`

---

### Task 3: Memorials

**Files:**
- Create: `backend/alembic/versions/0056_memorials.py`, `backend/app/services/memorial_service.py`, `backend/app/api/v1/memorials.py`, `frontend/components/memorials/{MemorialHeader,MemorializeDialog}.tsx`
- Modify: `backend/app/models/household.py` (+`passed_on date null`), `backend/app/models/user.py` (+`memorialized_at timestamptz null`), auth login + token refresh (reject memorialized), mention resolution / user pickers / nudge repos / ship-to people / recipient pickers (exclude `memorialized_at IS NOT NULL`), `celebration_repo.py` + `celebration_service.py` (kind `remembrance`), household page + profile page (memorial layout), admin users table action
- Test: `backend/tests/unit/services/test_memorial_service.py`, `backend/tests/unit/services/test_celebration_service.py` (extend), auth test, frontend MemorialHeader test

**Interfaces:**
- `MemorialService.set_passed_on(member_id, actor_id, passed_on: date | None)` — owner or admin (confirmed relatives added in wave 4.1 via `RelationService.is_confirmed_relative`); date not in future, not before birthday.
- `MemorialService.memorialize_user(user_id, admin_id, passed_on: date | None)` — admin only; sets `memorialized_at=now`, `is_active=False`, revokes sessions/refresh tokens, audit log; `unmemorialize` reverses (admin).
- Celebrations: memorialized/passed subjects emit `{kind: "remembrance", title: "Remembering <name>"}` on birthday and on `passed_on` anniversary; no "Celebrate" button; no birthday notifications.
- UI: header with dates "1931 – 2026", softened palette (tokens only), "Share a memory" = composer prefilled with @handle; profile shows memorial banner; no message/nudge buttons.
- [ ] Tests: memorialized user login → 401 `ACCOUNT_MEMORIALIZED`; @mention of memorialized user not tagged/notified; celebrations return remembrance on birthday; future passed_on → 422; non-owner member → 403.
- [ ] Implement → PASS → commit `feat(memorials): remembrance pages for relatives and pets`

---

### Task 4: Wave polish + PR (orchestrator)

- [ ] Migrate local DBs to 0056; full suites; lint/type/format.
- [ ] Eval: create event → album exists; set end 20 h ago → run `albums.remind` → Maya notified; slideshow on TV-size viewport + keyboard; recipe CRUD + search + list link; memorialize a demo user → login refused, calendar shows "Remembering".
- [ ] Screenshots light/dark/phone; copy + empty states ("No recipes yet. Add the one everyone asks for."); `/simplify`.
- [ ] Push; PR "feat: engagement wave 2 — content" on wave-1 PR.
