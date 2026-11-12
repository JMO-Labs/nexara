# Developer Guide

This section is for contributors and integrators working on Nexara itself. The
project is a monorepo: a FastAPI backend in `backend/` and a Next.js frontend
in `frontend/`, backed by PostgreSQL 16, Valkey, and Celery workers.

## Where to start

- **[Architecture](architecture.md)** -- Backend layering, the frontend stack,
  multi-tenancy, realtime delivery, and background jobs.
- **[Contributing](contributing.md)** -- Fork, branch, test-driven workflow,
  commit conventions, pull requests, and CI/CD.
- **[API Reference](api-reference.md)** -- Where to find the REST API and the
  generated source documentation.

## Environment setup

The [Development](../development.md) page covers installing dependencies and
running the backend, frontend, and workers locally. Come back here once the
stack is running.

## Principles

- Keep layers strict: routes call services, services call repositories.
- Scope every query by community.
- Write the failing test first.
- Keep files short and well documented.

If something here is unclear or out of date, fixing the documentation is a
welcome first contribution.
