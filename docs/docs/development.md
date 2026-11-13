# Development Guide

Architecture, conventions, and testing practices for Nexara contributors.

## Architecture Overview

```
Clients (Nuxt 3 SPA / PWA)
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

## Frontend Architecture

The Nuxt 3 frontend uses:

- **Pinia** for state management
- **Composables** for reusable logic (API client, WebSocket, SSE, dark mode)
- **Flowbite** for UI components
- **Tailwind CSS** for styling

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

- **Framework:** pytest + pytest-asyncio
- **Database:** Real PostgreSQL (no SQLite in tests)
- **Coverage:** pytest-cov with HTML and Cobertura reports

```bash
cd backend
pytest --cov=app --cov-report=html -v
```

### Frontend

- **Framework:** Vitest + Vue Test Utils
- **E2E:** Playwright (manual CI trigger)
- **Coverage:** V8 coverage provider

```bash
cd frontend
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

### Security checks in `scripts/wq-ci-test.sh`

The GitHub test script also runs, and fails on any finding:

- `pip-audit` on the frozen backend dependencies (`uv export --frozen --no-hashes`).
  Fix by upgrading the package in `uv.lock`.
- `bandit -r backend/app -ll -q` (medium severity and above). Fix the finding, or
  add `# nosec <id>` with a comment explaining why it is a false positive.
- `npm audit --omit=dev --audit-level=high` in `frontend`.

Gitleaks stays GitLab-only.
