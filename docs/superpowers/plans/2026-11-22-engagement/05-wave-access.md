# Wave 5 — Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simple mode, printable monthly newsletter, reply-by-email.

**Architecture:** Three independent tasks (parallel), then a final phase polish. Simple mode is CSS + nav filtering. Newsletter is a print-styled page. Reply-by-email uses stdlib `imaplib` + `email`.

**Spec:** `00-overview.md`. **Branch:** `feat/eng-w5-access` from `feat/eng-w4-connection`.

---

### Task 1: Simple mode

**Files:**
- Create: `backend/alembic/versions/0064_simple_mode.py`, `frontend/components/layout/SimpleModeSync.tsx`
- Modify: `backend/app/models/user_settings.py` (+`simple_mode bool default false`), settings schemas, admin users API (`PATCH /admin/users/{id}/settings {simple_mode}` → audit), `frontend/app/globals.css` (`[data-simple]` rules), SideNav/BottomTabBar/MoreSheet (filter), Settings Display tab toggle, admin users table action, components with hover-only controls (PostCard action menu, list row actions, gallery item actions — make visible in simple mode)
- Test: backend settings/admin API tests, `frontend/tests/unit/components/layout/simple-mode.test.tsx`

**Interfaces:**
- `SimpleModeSync` sets `document.documentElement.dataset.simple = "1"` when setting on.
- CSS: `:root[data-simple] { font-size: 125%; }` plus `--tap-min: 48px` used by buttons; `[data-simple] .hover-only { opacity: 1 }` (add `hover-only` class at the hover-reveal sites).
- `SIMPLE_NAV = ["feed","photos","family","calendar"]` — nav components render only these when simple; More sheet keeps "Settings" + "Turn off simple mode".
- [ ] Tests: setting on → `data-simple` attribute present; nav shows exactly 4 primary items + settings; admin non-admin PATCH → 403; post actions visible without hover in simple mode.
- [ ] Implement → PASS → commit `feat(a11y): simple mode with larger text and fewer menus`

---

### Task 2: Printable newsletter

**Files:**
- Create: `backend/alembic/versions/0065_newsletter.py`, `backend/app/services/newsletter_service.py`, `backend/app/api/v1/newsletter.py`, `backend/app/schemas/newsletter.py`, `frontend/app/app/newsletter/[month]/page.tsx`, `frontend/components/newsletter/{NewsletterView,NewsletterAdminBar}.tsx`, `frontend/app/print.css` (imported by the page)
- Modify: recap monthly email (link to newsletter), nav "More" entry
- Test: `backend/tests/unit/services/test_newsletter_service.py`, frontend view test

**Interfaces:**
- Table `newsletter_overrides(community_id, month char(7) 'YYYY-MM', post_id, action check in ('pin','hide'), created_by, pk(community_id, month, post_id))`.
- `NewsletterService.build(month: str, viewer_id) -> Newsletter{month, top_posts ≤8 (by reactions+comments, visible to viewer, pinned first, hidden removed), photos ≤12, birthdays, remembrances, new_recipes, opened_capsules (viewer is recipient), events[{title, date, place}]}`; month must be ≤ current month and ≥ community creation → else 404.
- `PUT /api/v1/admin/newsletter/{month}/overrides {post_id, action|null}`.
- Places shown as a text list (ponytail: printed tile maps need a static-map service; add if asked).
- Print CSS: A4/Letter, `@page { margin: 16mm }`, two-column masthead, avoid breaks inside cards, hide app chrome, links printed as text, photos `max-height: 60mm`.
- [ ] Tests: post in group viewer isn't in → absent; hidden override removes; pinned first; future month → 404.
- [ ] UI: page with "Print or save as PDF" (`window.print()`), admin bar (pin/hide per post) only for admins and not printed.
- [ ] Implement → PASS → commit `feat(newsletter): printable monthly family newsletter`

---

### Task 3: Reply by email

**Files:**
- Create: `backend/alembic/versions/0066_reply_email.py`, `backend/app/models/reply_token.py`, `backend/app/repositories/reply_token_repo.py`, `backend/app/services/email/reply_parse.py`, `backend/app/services/email/inbound_service.py`, `backend/app/services/email_reply_admin_service.py`, `backend/app/api/v1/admin_email_reply.py`, `backend/app/tasks/inbound_email_tasks.py`, `frontend/components/admin/EmailRepliesTab.tsx`
- Modify: `backend/app/models/community.py` (+`inbound_imap_host, inbound_imap_port int default 993, inbound_imap_user, inbound_imap_password (Fernet, write-only), inbound_reply_address`), `backend/app/tasks/notification_tasks.py` (`Reply-To` header for `comment`, `mention`, `new_post` emails when feature on + configured), `celery_app.py`, admin nav
- Test: `backend/tests/unit/services/email/test_reply_parse.py`, `backend/tests/unit/services/email/test_inbound_service.py`, admin API test

**Interfaces:**
- Table `reply_tokens(token_hash char(64) pk (sha256 hex), community_id, user_id, post_id, expires_at = now+30d, created_at)`; raw token = `secrets.token_urlsafe(18)`; address `local+<token>@domain` from `inbound_reply_address`.
- `reply_parse.extract_token(addresses: list[str], base_local: str) -> str | None`; `reply_parse.clean_body(msg: email.message.Message) -> str` — prefer text/plain, else HTML stripped of tags; cut at first line matching `^On .* wrote:$`, `^-----Original Message-----`, `^From: `, or quoted `>` block; drop `-- ` signature and trailing whitespace; cap 5000 chars; empty → None.
- `InboundService.process(msg) -> Literal["posted","ignored"]` — token valid + unexpired + user active + user can still view post (existing comment service checks) → `CommentService.create(post_id, user_id, body)`; rate limit 20/hour/user; ignores auto-replies (`Auto-Submitted` ≠ `no`, `Precedence: bulk|list|auto_reply`).
- Beat every minute `inbound_email.poll` (only communities with feature on + config): `imaplib.IMAP4_SSL`, `SELECT INBOX`, `SEARCH UNSEEN`, max 50 per run, process, then `STORE +FLAGS \Deleted` + `EXPUNGE`. Network errors logged, never raised.
- Admin: `GET/PUT /api/v1/admin/email-reply`, `POST /admin/email-reply/test` (login + select only). Tab with fields, test button, short setup steps (create a mailbox, enable IMAP, use an app password, set catch-all/plus-addressing).
- [ ] Tests: Gmail/Outlook/Apple Mail quoted samples cleaned to just the reply; signature stripped; expired token ignored; user blocked by post author → ignored; out-of-office (`Auto-Submitted: auto-replied`) ignored; 21st reply in hour ignored; secret never returned by GET.
- [ ] Implement → PASS → commit `feat(email): reply to notifications by email`

---

### Task 4: Final phase polish + PR (orchestrator)

- [ ] Migrate local DBs to 0066; full suites; lint/type/format.
- [ ] Eval: simple mode as Ruth (screenshots phone + desktop); newsletter print preview (Chromium `page.pdf`) light; reply-by-email via a local test IMAP (GreenMail container, eval only) end to end.
- [ ] Phase-wide pass: every feature flag off → UI hidden, API 404; recap email includes all wave sections; a11y sweep (axe via Playwright) on new pages; `/simplify` across phase diff.
- [ ] Push; PR "feat: engagement wave 5 — access" on wave-4 PR; update memory `nexara-profiles-household-plan.md` with phase status.
