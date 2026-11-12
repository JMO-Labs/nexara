# Development Guide

Architecture, conventions, and workflow for Nexara contributors.

## Architecture Overview

```
Clients (Next.js 16 app / PWA)
    |
    | HTTP / WebSocket / SSE
    v
FastAPI (async, api/v1)
    |
    +---> PostgreSQL 16 + FTS
    +---> Valkey (pub/sub, cache)
    +---> S3 / Local storage
    +---> Celery task queue
```

### Backend

The FastAPI backend is async (SQLAlchemy 2.0) with a strict layering:

```
api/v1/<router>.py
  --> services/<x>_service.py
    --> repositories/<x>_repo.py
      --> models/<x>.py
```

- Routes validate input (Pydantic), call a service, return a response schema.
  Routes never import repositories directly.
- Services hold business logic and receive `(repo, community_id, session, ...)`
  via dependency injection from `core/dependencies.py`.
- Repositories own all queries and always filter on `community_id`
  (multi-tenancy) and soft-delete (`deleted_at IS NULL`).
- Errors use `core/exceptions.py` and the standard
  `{ "error": { "code", "message", "details" } }` envelope.

### Frontend

- **Next.js 16** App Router with **React 19**
- **Tailwind v4** and **shadcn/ui** (Radix) in `components/ui`
- **TanStack Query** for server state, **zustand** for client state
- **next-intl** for i18n, **next-themes** for dark mode

## Backend Development

```bash
cd backend
uv venv .venv && source .venv/bin/activate && uv sync
uvicorn app.main:app --reload --port 8000
alembic upgrade head
alembic revision -m "msg"
celery -A app.tasks.celery_app worker --loglevel=info
```

Check `alembic heads` before creating a migration and set `down_revision` to
the current head.

## Frontend Development

```bash
cd frontend
npm install && npm run dev
npm run build
```

## Code Style

```bash
# Backend
cd backend
ruff check . && ruff format --check .
mypy app/

# Frontend
cd frontend
npx eslint . && npx prettier --check .
```

Files stay under 400 lines. Public modules, classes, and functions carry
Doxygen-style comments (`@file`, `@brief`, `@param`, `@return`).

## Testing Workflow

Write a failing test first, then the code, then refactor.

### Backend

pytest with pytest-asyncio (`asyncio_mode = auto`) against a real PostgreSQL.
Unit tests use `AsyncMock(spec=Repo)` and `MagicMock(spec=Model)`.

```bash
cd backend
pytest --cov=app --cov-report=html -v
pytest tests/unit/services/test_event_service.py -xvs
```

### Frontend

Vitest with Testing Library; Playwright for end-to-end (manual in CI).

```bash
cd frontend
npm test
npx vitest run --coverage
npx playwright test
```

## Git Workflow

Branch from `dev` (for example `feat/short-name`) and open a PR/MR back to
`dev`. Never push to `main`. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/): no emojis,
subject of 72 characters or fewer, and reference the issue number.

```
feat(events): add RSVP labels (nexara#12)
fix: correct CORS header for WebSocket upgrade
docs: update deployment guide
test: add integration tests for feed pagination
chore: update CI pipeline caching strategy
```

Pre-commit runs `ruff check`, `ruff format --check`, `mypy app/`, `eslint`
and `prettier --check`. Maintain or improve coverage on every PR.

## CI/CD Overview

The GitLab pipeline (mirrored on GitHub) runs on merge requests and pushes.
See `.gitlab-ci.yml` and `.gitlab/ci/`.

| Stage    | Jobs                                   |
| -------- | -------------------------------------- |
| lint     | Ruff, mypy, ESLint, Prettier           |
| test     | pytest (+ PostgreSQL), Vitest          |
| security | Bandit, pip-audit, npm audit, gitleaks |
| build    | Docker image via Kaniko                |
| scan     | Trivy container vulnerability scan     |
| e2e      | Playwright (manual)                    |
| report   | Coverage badges                        |
| pages    | MkDocs + Doxygen + reports             |
| release  | Release on version tags                |
