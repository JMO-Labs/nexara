# Development Guide

Architecture, conventions, and testing practices for Nexara contributors.

## Architecture Overview

```
Clients (Next.js 16 / React 19 PWA)
    |
    | HTTP / WebSocket / SSE
    v
FastAPI (api/v1)
    |
    +---> PostgreSQL + FTS
    +---> Valkey (pub/sub, cache)
    +---> S3 / Local storage
    +---> Celery task queue
```

## Backend Architecture

The FastAPI backend follows a strict layered architecture:

```
Routes (app/api/v1/)
  --> Services (app/services/)
    --> Repositories (app/repositories/)
      --> Models (app/models/)
```

**Rules:**

- Route handlers validate input (Pydantic), call a service, return a response schema
- Services contain business logic and call repositories
- Repositories handle all database operations
- Never import repositories directly in route files
- Every query is scoped by `community_id`; errors use the standard envelope from `core/exceptions.py`

## Frontend Architecture

The Next.js 16 (App Router) frontend uses:

- **React 19** for UI
- **TanStack Query** for server state (`lib/api`, hooks)
- **zustand** for client state (stores)
- **shadcn/ui** (Radix) components in `components/ui`
- **Tailwind CSS v4** for styling
- **next-intl** and **next-themes** for i18n and dark mode

## Code Style

| Tool     | Scope    | Purpose                |
| -------- | -------- | ---------------------- |
| Ruff     | Backend  | Linting and formatting |
| mypy     | Backend  | Type checking          |
| ESLint   | Frontend | Linting                |
| Prettier | Frontend | Formatting             |

Run all linters locally:

```bash
# Backend
ruff check backend/
ruff format --check backend/
mypy backend/app/

# Frontend
cd frontend
npx eslint .
npx prettier --check .
```

## Testing

### Backend

- **Framework:** pytest + pytest-asyncio (`asyncio_mode = auto`)
- **Database:** Real PostgreSQL (no SQLite in tests)
- **Coverage:** pytest-cov with HTML and Cobertura reports

```bash
cd backend
pytest --cov=app --cov-report=html -v
```

### Frontend

- **Framework:** Vitest
- **E2E:** Playwright (manual CI trigger)
- **Coverage:** V8 coverage provider

```bash
cd frontend
npm run dev                # dev server
npm test                   # Vitest
npx vitest run --coverage
```

## Git Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user registration endpoint
fix: correct CORS header for WebSocket upgrade
docs: update deployment guide with Helm instructions
test: add integration tests for feed pagination
chore: update CI pipeline caching strategy
```

## CI/CD Pipeline

The GitLab CI/CD pipeline runs automatically on merge requests and pushes
to `main`. See `.gitlab-ci.yml` and `.gitlab/ci/` for the full configuration.

| Stage    | Jobs                                          |
| -------- | --------------------------------------------- |
| lint     | Ruff, mypy, ESLint, Prettier                  |
| test     | pytest (+ PostgreSQL), Vitest                  |
| security | Bandit, pip-audit, npm audit, gitleaks         |
| build    | Docker image via Kaniko                        |
| scan     | Trivy container vulnerability scan             |
| e2e      | Playwright (manual)                            |
| report   | Coverage badges                                |
| pages    | MkDocs + Doxygen + reports                     |
| release  | GitLab Release on version tags                 |
