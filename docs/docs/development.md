# Development Guide

Architecture, workflow, and conventions for Nexara contributors.

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
    +---> S3 / local storage
    +---> Celery task queue
```

### Backend

FastAPI with async SQLAlchemy 2.0 and a strict layered architecture:

```
api/v1/<router>.py -> services/<x>_service.py -> repositories/<x>_repo.py -> models/<x>.py
```

- Routes validate input (Pydantic), call a service, return a schema. Routes never import repositories.
- Services hold business logic and receive `(repo, community_id, session, ...)` via DI from `core/dependencies.py`.
- Repositories own all queries; every query filters on `community_id` (multi-tenancy) and soft-deleted rows.
- Errors use `core/exceptions.py` and are returned in the `{ "error": { "code", "message", "details" } }` envelope.
- Migrations are managed with alembic; always set `down_revision` to the current head (`alembic heads`).
- Celery queues: `default`, `maintenance`, `notifications`, `email`, `media`.

### Frontend

Next.js 16 (App Router) with React 19:

- **Tailwind v4** for styling, tokens in `app/globals.css`
- **shadcn/ui** (Radix) components in `components/ui`, Lucide icons
- **TanStack Query** for server state, **zustand** for client state
- **next-intl** for i18n, **next-themes** for dark mode

UI must meet WCAG 2.1 AA: ARIA labels, keyboard navigation, contrast.

## Backend Development

```bash
cd backend
uv venv .venv && source .venv/bin/activate && uv sync   # install
uvicorn app.main:app --reload --port 8000               # dev server
alembic upgrade head                                     # migrate
alembic revision -m "msg"                                # new migration
celery -A app.tasks.celery_app worker --loglevel=info   # worker
celery -A app.tasks.celery_app beat --loglevel=info     # beat
```

Lint and type-check:

```bash
ruff check . && ruff format --check .
mypy app/
```

## Frontend Development

```bash
cd frontend
npm install && npm run dev      # dev server
npm run build                   # production build
npx eslint . && npx prettier --check .
```

## Testing Workflow

Write a failing test first, then the code, then refactor.

### Backend

pytest with `pytest-asyncio` (mode `auto`) against a real PostgreSQL (no SQLite).
Unit tests use `AsyncMock(spec=Repo)` and `MagicMock(spec=Model)`.

```bash
cd backend
pytest --cov=app --cov-report=html -v                    # full
pytest tests/unit/services/test_event_service.py -xvs    # single file
```

### Frontend

Vitest with Testing Library; Playwright for e2e (manual in CI).

```bash
cd frontend
npm test                                  # vitest run
npx vitest run --coverage
npx vitest run tests/unit/X.test.ts       # single file
npx playwright test                       # e2e
```

## Git Workflow

- Branch from `dev`; open MRs/PRs against `dev`. Never push directly to `main`.
- Use [Conventional Commits](https://www.conventionalcommits.org/), subject of 72 characters or fewer, no emojis, reference the issue number:

```
feat(events): add RSVP labels (nexara#42)
fix: correct CORS header for WebSocket upgrade
docs: update deployment guide
test: add integration tests for feed pagination
chore: update CI caching
```

- Keep files under 400 lines; split modules when approaching the limit.
- Maintain or improve coverage on every MR/PR.
- Pre-commit checks: `ruff check`, `ruff format --check`, `mypy app/`, `eslint`, `prettier --check`.

## CI/CD Overview

GitLab CI/CD is primary and is mirrored on GitHub.

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

### Security checks in `scripts/wq-ci-test.sh`

The GitHub test script also runs, and fails on any finding:

- `pip-audit` on the frozen backend dependencies (`uv export --frozen --no-hashes`).
  Fix by upgrading the package in `uv.lock`.
- `bandit -r backend/app -ll -q` (medium severity and above). Fix the finding, or
  add `# nosec <id>` with a comment explaining why it is a false positive.
- `npm audit --omit=dev --audit-level=high` in `frontend`.

Accepted pip-audit advisories (no upstream fix, passed via `--ignore-vuln`):

| ID              | Package     | Why it does not apply                                         |
|-----------------|-------------|---------------------------------------------------------------|
| PYSEC-2026-1325 | ecdsa       | Minerva timing on signing; we sign RS256 via `cryptography`.  |
| PYSEC-2026-4298 | python-jose | HMAC key confusion; decode pins `algorithms=[JWT_ALGORITHM]`. |

Gitleaks stays GitLab-only.

The documentation site is published to GitHub Pages at
<https://jmo-labs.github.io/nexara>.
