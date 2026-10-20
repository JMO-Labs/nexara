# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Nexara — self-hosted community platform (families/clubs/groups). Monorepo: `backend/` (FastAPI) + `frontend/` (Nuxt 3). Postgres 16, Valkey (Redis), Celery. Container-native. GitLab CI/CD primary; mirrored on GitHub.

## Commands

### Backend (`cd backend`)

```bash
uv venv .venv && source .venv/bin/activate && uv sync   # install
uvicorn app.main:app --reload --port 8000               # dev server
pytest --cov=app --cov-report=html -v                   # full tests
pytest tests/unit/services/test_event_service.py -xvs   # single file
pytest tests/unit/services/test_event_service.py::TestRSVP::test_rsvp_creates_attendance  # single test
ruff check . && ruff format --check .                   # lint
mypy app/                                                # types (strict)
alembic upgrade head                                     # migrate
alembic revision -m "msg"                                # new migration
celery -A app.tasks.celery_app worker --loglevel=info   # worker
celery -A app.tasks.celery_app beat --loglevel=info     # beat
```

Tests need a real Postgres (no SQLite). `pytest-asyncio` mode = `auto`.

### Frontend (`cd frontend`)

```bash
npm install && npm run dev          # dev (Nuxt)
npm run build                       # production build
npm test                            # vitest run
npx vitest run --coverage
npx vitest run tests/unit/X.test.ts # single file
npx eslint . && npx prettier --check .
npx playwright test                 # e2e (manual in CI)
```

### Deploy

`cd deploy && cp .env.example .env && docker compose up -d` (proxy to `:8080`). Helm chart in `deploy/helm/nexara/`.

## Architecture

### Backend layering (strict)

`api/v1/<router>.py` → `services/<X>_service.py` → `repositories/<X>_repo.py` → `models/<X>.py`. **Routes never import repos directly.** Services receive `(repo, community_id, session, ...)` via DI from `core/dependencies.py`. Errors use `core/exceptions.py` (`AppError`, `NotFoundError`, `AuthorizationError`) — emitted as `{ "error": { "code", "message", "details } }` envelope.

### Multi-tenancy

Every row is scoped by `community_id` (default community via `COMMUNITY_DEFAULT` server_default in `models/user.py`). Every query in repos filters on it. `BaseRepository` (`repositories/base.py`) provides soft-delete (`deleted_at IS NULL`) and `apply_block_filter(stmt, viewer_id)` for user-blocking — call it on viewer-scoped reads.

### Visibility model

Common pattern: `visibility ∈ {community, subgroup, private}` + optional `subgroup_id`. Service `_can_view` checks: community → all members; private → author only; subgroup → user must belong (`SubgroupMember` lookup). Repos build `OR` clauses inline (see `event_repo.list_in_range`).

### Async / sessions

SQLAlchemy 2.0 async (`Mapped[] / mapped_column`). Sessions injected per-request; repos call `_session.flush()` + `refresh()` after writes. JSONB used heavily (rsvp_labels, contribution_slots, etc.). FTS via computed `TSVECTOR` columns (`search_fts`) with GIN indexes — populated by `Computed(...)`, not triggers.

### Realtime + notifications

`services/realtime/events.py` defines `RealtimeEvent`; `EventBus` fans out to SSE (`api/v1/sse.py`) and WS (`api/v1/ws.py`). `NotificationService.notify(user_id, type, ...)` consults `user_settings` per-channel prefs via `PREF_MAP` — extend `PREF_MAP` when adding a new notif type. In-app + Web Push + email channels.

### Celery

`tasks/celery_app.py` — queues: `default`, `maintenance`, `notifications`, `email`, `media`. Beat schedule defined here. Beat singleton via `tasks/beat_lock.py` (sync psycopg2 advisory lock). Add new periodic jobs by appending to `beat_schedule` dict and routing the task to a queue.

### Migrations

Linear chain `0001 → 0007 → ...`. Two-tier filename style: ordinal `000N_*.py` (manual/main) and hash `<sha>_*.py` (auto-generated for sub-features like OAuth, polls). Always set `down_revision` to the current head — check `alembic heads` first.

### Frontend

React/Next.js - need more details

## Conventions

- File length ≤ **400 lines** — split modules when approaching.
- Doxygen-style comments (`@file`, `@brief`, `@param`, `@return`) on file/class/public-fn.
- TDD: failing test first. AsyncMock(spec=Repo) + MagicMock(spec=Model) is the unit-test idiom (see `tests/unit/services/test_event_service.py`).
- Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). No emojis. ≤72 char subject. Reference issue numbers.
- WCAG 2.1 AA for UI. ARIA labels, keyboard nav, contrast required.
- All errors via the standard envelope; never raise raw HTTP exceptions in services.

## CI/CD (GitLab)

Stages: lint → test → security (Bandit, pip-audit, npm audit, gitleaks) → build (Kaniko) → scan (Trivy) → e2e (manual) → report → pages → release. Pre-commit: `ruff check`, `ruff format --check`, `mypy app/`, `eslint`, `prettier --check`. Maintain or improve coverage on every MR.

## Plans / phases

`plans/phases/phase-N-<name>/phase_plan.md` is the source of truth for in-flight feature work, with per-component child specs (e.g. `10-calendar-events.md`). Group execution via `/superpowers:executing-plans`.
