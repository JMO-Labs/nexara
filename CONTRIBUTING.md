# Contributing to Nexara

Thank you for your interest in contributing to Nexara. This document covers the
process and conventions for contributing code, reporting issues, and proposing
features.

## Getting Started

1. Fork the repository on GitLab.
2. Clone your fork and create a feature branch from `main`:

```bash
git clone https://gitlab.com/<your-username>/nexara.git
cd nexara
git checkout -b feature/your-feature-name
```

3. Set up the development environment (see below).

## Development Environment

### Backend

```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv sync
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

See the [Development Guide](docs/docs/development.md) for full architecture and
tooling details.

## Code Standards

### General

- Keep files under **400 lines**. Split into submodules when approaching the limit.
- Use **descriptive names** for variables, functions, classes, and files.
- Add **Doxygen-style comments** (`@file`, `@brief`, `@param`, `@return`) to
  every file, class, and public function.
- Wrap all user-facing strings in i18n functions: `_()` (backend) or `$t()`
  (frontend).
- Follow existing module structure and separation of concerns.

### Backend (Python)

- **Linter/Formatter:** Ruff (linting and formatting).
- **Type checker:** mypy.
- **Architecture:** Routes -> Services -> Repositories -> Models. Never import
  repositories directly in route handlers.
- **Error handling:** All errors use the standard
  `{ "error": { "code", "message", "details" } }` envelope.
- **Database:** Every query scopes by `community_id`. Use soft-delete
  (`deleted_at IS NULL`) via `BaseRepository`.

### Frontend (TypeScript/Vue)

- **Linter:** ESLint.
- **Formatter:** Prettier.
- **Framework:** Nuxt 3 with Pinia, Tailwind CSS, and Flowbite.
- **Accessibility:** WCAG 2.1 AA target. Include ARIA labels, keyboard
  navigation, and color contrast on every UI component.

## Testing

All contributions must include tests. We practice TDD -- write the failing test
first, then implement the minimal code to make it pass.

### Backend

```bash
cd backend
pytest --cov=app --cov-report=html -v
```

- Framework: pytest + pytest-asyncio
- Database: Real PostgreSQL (no SQLite shortcuts)
- Target: Maintain or increase existing coverage

### Frontend

```bash
cd frontend
npx vitest run --coverage
```

- Framework: Vitest + @vue/test-utils
- Environment: happy-dom
- Target: Maintain or increase existing coverage

## Commit Messages

- Use [Conventional Commits](https://www.conventionalcommits.org/) style:
  `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Write a concise summary on the first line (72 chars max).
- No emojis.
- Reference issue numbers where applicable: `fix: handle empty search query (#42)`.

## Merge Request Process

1. Ensure all linters pass locally:

```bash
# Backend
ruff check backend/
ruff format --check backend/
mypy backend/app/

# Frontend
cd frontend && npx eslint . && npx prettier --check .
```

2. Ensure all tests pass with no regressions.
3. Create a merge request against `main` with a clear description of changes.
4. The CI pipeline will run lint, test, security, and build stages automatically.
5. At least one maintainer must approve before merging.

## Reporting Issues

- Use GitLab Issues with a clear title and description.
- Include steps to reproduce, expected behavior, and actual behavior.
- Attach logs or screenshots when relevant.

## License

By contributing to Nexara, you agree that your contributions will be licensed
under the [GNU General Public License v3.0](LICENSE).
