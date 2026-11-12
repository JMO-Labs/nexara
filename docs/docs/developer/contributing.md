# Contributing

Thanks for helping improve Nexara. This page describes the workflow we expect
for every change.

## Fork and clone

Fork the repository, clone your fork, and add the upstream remote. Base your
work on the `dev` branch; never target `main`.

```bash
git remote add upstream <upstream-url>
git fetch upstream dev
```

## Branch naming

Create a branch from `dev` with a descriptive prefix:

- `polish/phase-N-<topic>` for work belonging to a planned phase.
- `feat/<topic>`, `fix/<topic>`, `docs/<topic>` for other changes.

Plans for in-flight work live in `plans/phases/phase-N-<name>/phase_plan.md`.

## Test-driven development

Tests come first:

1. Write a failing test that describes the behavior.
2. Write the smallest change that makes it pass.
3. Refactor with the tests green.

Backend tests use pytest against a real PostgreSQL (no SQLite). Unit tests use
the `AsyncMock(spec=Repo)` and `MagicMock(spec=Model)` idiom; see
`tests/unit/services/test_event_service.py`. Frontend tests use vitest, with
Playwright for end-to-end checks. Maintain or improve coverage on every merge
request.

## Code style

- Keep files under 400 lines; split modules as they grow.
- Add Doxygen-style comments (`@file`, `@brief`, `@param`, `@return`) to files,
  classes, and public functions.
- Backend: `ruff check`, `ruff format --check`, and `mypy app/` (strict).
- Frontend: `eslint` and `prettier --check`.
- Meet WCAG 2.1 AA for any UI change.

## Conventional commits

Use `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, or `chore:`, with a subject
of 72 characters or fewer, no emojis, and the issue number referenced:

```
feat(events): add RSVP labels (#42)
```

## Pull requests

Open a pull request against `dev`. Describe what changed and why, link the
issue, and list any decisions you made. Keep pull requests focused; a small
diff is reviewed faster.

## CI/CD

GitLab CI runs these stages: lint, test, security (Bandit, pip-audit,
npm audit, gitleaks), build (Kaniko), scan (Trivy), e2e (manual), report,
pages, and release. Run the linters and the tests you touched locally before
pushing, and make sure the pipeline is green before requesting review.

## Documentation

Docs live in `docs/docs/`. Navigation is directory-based: add a Markdown file to
the right folder and list it in that folder's `.pages` file to control order.
There is no central `nav:` in `mkdocs.yml`, so parallel doc changes rarely
conflict.

## Secrets

Never commit credentials, tokens, or keys. Gitleaks runs in CI and will fail the
pipeline.
