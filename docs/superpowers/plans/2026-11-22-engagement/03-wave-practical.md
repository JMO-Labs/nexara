# Wave 3 — Practical Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shared expenses, event rides, chore rotation.

**Architecture:** Three independent tasks (parallel), then polish. Money in integer cents. Rides are own tables (contribution slots can't hold seat/time data). Chores extend list items + reuse `ListItemAssignment`/`ListActivity`.

**Spec:** `00-overview.md`. **Branch:** `feat/eng-w3-practical` from `feat/eng-w2-content`.

---

### Task 1: Shared expenses

**Files:**
- Create: `backend/alembic/versions/0057_expenses.py`, `backend/app/models/expense.py`, `backend/app/repositories/expense_repo.py`, `backend/app/schemas/expense.py`, `backend/app/services/expense_math.py`, `backend/app/services/expense_service.py`, `backend/app/api/v1/expenses.py`, `backend/app/services/notifications/types/expense_added.py`, `frontend/lib/api/expenses.ts`, `frontend/app/app/expenses/{page,[id]/page}.tsx`, `frontend/components/expenses/{LedgerForm,ExpenseForm,BalanceList,SettleDialog}.tsx`
- Modify: event detail ("Shared costs" link/create), wishlist item ("Split this gift"), nav (icon `Receipt`), admin settings general (community currency select — column from 1.1)
- Test: `backend/tests/unit/services/test_expense_math.py`, `backend/tests/unit/services/test_expense_service.py`, frontend form tests

**Interfaces:**
- Tables: `expense_ledgers(id, community_id, name ≤80, currency char(3), event_id null, wishlist_id null, created_by, created_at, archived_at null)`, `ledger_members(ledger_id, user_id, pk both)`, `expenses(id, ledger_id, payer_id, amount_cents int >0, description ≤200, spent_on date, created_by, created_at, deleted_at)`, `expense_shares(expense_id fk cascade, user_id, amount_cents int ≥0, pk both)`, `settlements(id, ledger_id, from_user_id, to_user_id, amount_cents >0, created_by, created_at)`.
- `expense_math.equal_split(amount_cents: int, user_ids: list[UUID]) -> dict[UUID,int]` — floor each, remainder +1 to first members in given order.
- `expense_math.net_balances(expenses, shares, settlements) -> dict[UUID,int]` (positive = owed money).
- `expense_math.simplify(balances: dict[UUID,int]) -> list[tuple[UUID,UUID,int]]` — greedy: repeatedly match largest debtor with largest creditor; output `(from, to, cents)`.
- Service: ledger CRUD (creator/admin edits; members view), `add_expense(ledger_id, actor, ExpenseIn{payer_id, amount_cents, description, spent_on, split: "equal"|"custom", shares?})` — payer and share users must be members; custom shares must sum exactly; `settle(ledger_id, actor, from, to, cents)` — actor must be `from` or `to`; non-members → 404.
- [ ] Tests: `equal_split(1000,[a,b,c]) == {a:334,b:333,c:333}`; custom shares 600+300 for 1000 → 422 `SHARES_MISMATCH`; simplify of A+50,B−30,C−20 → [(B,A,30),(C,A,20)]; settle reduces balance to 0; sum of balances always 0 (property-style loop over 50 random ledgers, seeded); non-member GET → 404.
- [ ] UI: ledger list; ledger page = balances ("Maya owes Ruth $40" with Settle button), expenses list, add form (amount via `inputmode="decimal"`, currency from ledger, split toggle). Format with `Intl.NumberFormat(locale,{style:"currency",currency})`.
- [ ] Implement → PASS → commit `feat(expenses): shared expense ledgers with simplified debts`

---

### Task 2: Event rides

**Files:**
- Create: `backend/alembic/versions/0058_event_rides.py`, `backend/app/models/event_ride.py`, `backend/app/repositories/ride_repo.py`, `backend/app/schemas/ride.py`, `backend/app/services/ride_service.py`, `backend/app/api/v1/rides.py`, `backend/app/services/notifications/types/ride_update.py`, `frontend/lib/api/rides.ts`, `frontend/components/events/rides/{RidesSection,OfferRideForm,RideCard}.tsx`
- Modify: event detail body (mount `RidesSection` when feature on)
- Test: `backend/tests/unit/services/test_ride_service.py`, `backend/tests/integration/repositories/test_ride_repo.py` (seat race), frontend tests

**Interfaces:**
- Tables: `event_rides(id, community_id, event_id fk cascade, kind text check in ('offer','request'), user_id, seats int check 1..8 (offers; requests = seats needed 1..8), origin text ≤120, depart_at timestamptz null, note ≤200, created_at, deleted_at)`, `ride_passengers(ride_id fk cascade, user_id, created_at, pk both)`.
- Service (all require viewer can view event — reuse `EventService._can_view` via service call): `offer`, `request`, `join(ride_id, user)` (row lock `SELECT … FOR UPDATE`; full → 409 `RIDE_FULL`; can't join own; one seat per user per event), `leave`, `answer_request(request_id, driver_offer_id, driver)` (adds requester(s) to offer, closes request), `cancel(ride_id, owner)` (notifies passengers).
- Notifications `ride_update` to driver on join/leave, to passengers on cancel/answer.
- [ ] Tests: two concurrent joins for last seat → one 409 (integration, two sessions); user who can't see private event → 404; joining second ride same event → 409 `ALREADY_RIDING`; cancel notifies 2 passengers.
- [ ] UI: section "Rides" with Offer a ride / Need a ride; cards show driver, seats left, from, leave time, join button; requests list with "I can take them".
- [ ] Implement → PASS → commit `feat(events): ride offers and requests`

---

### Task 3: Chore rotation

**Files:**
- Create: `backend/alembic/versions/0059_chore_rotation.py`, `backend/app/services/chore_service.py`, `backend/app/tasks/chore_tasks.py`, `frontend/components/lists/RepeatRotationField.tsx`
- Modify: `backend/app/models/list.py` (item columns), list item schemas/service (set repeat/rotation), `celery_app.py`, list item edit UI, `recap_sections.py` (+ "Your chores this week")
- Test: `backend/tests/unit/services/test_chore_service.py`, `backend/tests/unit/tasks/test_chore_tasks.py`, frontend field test

**Interfaces:**
- Columns on list items: `repeat text null check in ('daily','weekly','monthly')`, `rotation uuid[] default '{}'`, `rotation_index int default 0`, `next_due_at timestamptz null`.
- `next_due(prev: datetime, repeat: str) -> datetime` — monthly clamps day (Jan 31 → Feb 28/29).
- `ChoreService.advance(item, now) -> None`: if current assignment not done → activity `action="missed"`; `rotation_index = (i+1) % len(rotation)`; create `ListItemAssignment` for next assignee (status pending), un-complete item, `next_due_at = next_due(...)`, notify `list.assigned`. Rotation users must be list members (validated on save); removed members skipped at advance time.
- Beat `chores.advance_due` every 15 min: items with `next_due_at <= now` (lock per item; idempotent via `next_due_at` moving forward).
- [ ] Tests: weekly item with rotation [A,B,C], A didn't finish → missed logged, B assigned, due +7d; completed → no "missed"; Jan 31 monthly → Feb 28 (2027); member removed from list skipped; running task twice → one advance.
- [ ] UI: in item edit: Repeat (Never/Daily/Weekly/Monthly) + ordered people picker (drag or up/down buttons — buttons for a11y); item row shows "Next: Maya · Sun".
- [ ] Implement → PASS → commit `feat(lists): repeating chores with rotation`

---

### Task 4: Wave polish + PR (orchestrator)

- [ ] Migrate local DBs to 0059; full suites; lint/type/format.
- [ ] Eval: ledger for BBQ event, 3 expenses, balances + settle; ride offer 2 seats, Maya + Ruth join, third → full; weekly chore rotation advanced by running task.
- [ ] Screenshots, copy, focus, phone; `/simplify`.
- [ ] Push; PR "feat: engagement wave 3 — practical" on wave-2 PR.

---

### Task 5 (added 2026-11-22, user request): Recipe → shopping list

**Files:**
- Create: `backend/app/services/recipe_shopping_service.py`, `backend/app/schemas/recipe_shopping.py`, `frontend/components/recipes/AddToListDialog.tsx`
- Modify: `backend/app/api/v1/recipes.py` (route), `backend/app/core/dependencies.py` (DI), `frontend/lib/api/recipes.ts`, `frontend/components/recipes/RecipeView.tsx` (button)
- Test: `backend/tests/unit/services/test_recipe_shopping_service.py`, one real-Postgres test, `frontend/tests/unit/recipes/AddToListDialog.test.tsx`

**Interfaces:**
- `POST /api/v1/recipes/{recipe_id}/shopping-list` body `ToListIn{list_id: UUID | None = None, ingredients: list[int] | None = None (indexes; None = all), servings_note: bool = False}` → `ToListOut{list_id, added: int}` (201).
- Recipe must be visible to the actor (404 otherwise); `recipes` flag on.
- `list_id` given: the actor must be able to add items (reuse `ListItemService.create`, which enforces owner); target field = first `type_key == "text"` field with `required`, else first text field; none → 422 `LIST_HAS_NO_TEXT_FIELD`.
- `list_id` omitted: create a list via the existing list service: title `"Shopping: <recipe title>"` (≤ title max), `visibility="private"`, `field_schema=[{"key":"item","label":"Item","position":0,"required":true,"type_key":"text"}]`.
- Each selected ingredient → one item `values={field_key: "<qty> <item>".strip()}`, `recipe_id=recipe.id`, positions appended after existing items; blank ingredients skipped; out-of-range index → 422.
- Frontend: "Add to shopping list" button (icon ShoppingCart) on RecipeView when the recipe has ingredients → dialog: ingredient checkboxes (all checked), radio "New shopping list" / "Add to an existing list" + select of the viewer's own active lists, submit → toast "Added N items" with a link to the list.
