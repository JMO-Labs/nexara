# Nexara

📚 [View Documentation](https://jmo-labs.github.io/nexara) | 🐛 [Report Issues](https://github.com/JMO-Labs/nexara/issues) | 📖 [Contributing Guide](https://jmo-labs.github.io/nexara/developer/contributing/)

[![Docs](https://img.shields.io/badge/docs-latest-blue)](https://jmo-labs.github.io/nexara)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Build Status](https://github.com/JMO-Labs/nexara/actions/workflows/docs-deploy.yml/badge.svg)](https://github.com/JMO-Labs/nexara/actions/workflows/docs-deploy.yml)
[![Pipeline Status](https://gitlab.com/richardsoto1010/nexara/badges/main/pipeline.svg)](https://gitlab.com/richardsoto1010/nexara/-/pipelines)

---

A modern, fast, and attractive platform for small communities (families, clubs,
groups) to share events, photos, messages, and more. Self-hosted first,
container-native, and scaleable to Kubernetes.

## Features

- **Activity Feed** -- Posts with Markdown, GIFs, threaded comments, and reactions
- **Media Sharing** -- Photo and video upload with web-optimized transcoding
- **Calendar & Events** -- Recurring events, RSVP, contribution planner, iCal export
- **Real-time Chat** -- WebSocket-based group and direct messaging
- **Subgroups** -- Scoped feeds, events, and chat channels
- **Galleries** -- Named albums with bulk upload and access controls
- **Polls** -- Single, multiple-choice, yes/no, and photo polls with live results
- **Search** -- Full-text search across all content via PostgreSQL FTS
- **Notifications** -- In-app (SSE), push (Web Push), and email
- **SSO/OAuth2** -- Multi-provider OIDC/OAuth2 with admin UI, PKCE, and group-to-role mapping
- **Admin Panel** -- User management, roles, SSO providers, audit log, community settings
- **PWA** -- Installable progressive web app with offline shell
- **Plugin System** -- Extensible via backend hooks and frontend slots

## Tech Stack

| Layer          | Technology                                    |
| -------------- | --------------------------------------------- |
| Frontend       | Next.js 16, React 19, Tailwind v4, shadcn/ui  |
| Backend        | FastAPI (async), SQLAlchemy 2.0, Celery, Alembic          |
| Database       | PostgreSQL 16+                                 |
| Cache/Pub-Sub  | Valkey (Redis-compatible)                      |
| Storage        | Local filesystem (default), S3-compatible opt  |
| Containers     | Alpine-based Docker, 2 containers max          |

## Quick Start

```bash
cd deploy
cp .env.example .env
# Edit .env with SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_ORIGINS

docker compose up -d
```

Point your reverse proxy (Nginx Proxy Manager, Caddy, Traefik, etc.) to
`http://{host_ip}:8080` and enable SSL.

## Development

```bash
# Backend
cd backend && uv venv .venv && source .venv/bin/activate && uv sync
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

See the [Development Guide](docs/docs/development.md) for architecture details.

## Documentation

Full documentation lives at **<https://jmo-labs.github.io/nexara>** (GitHub
Pages, MkDocs Material). Start with
[Getting Started](docs/docs/getting-started.md) or the
[Development Guide](docs/docs/development.md). A mirror is also published to
GitLab Pages on every push to `main`:

- **Project Docs** -- MkDocs Material site
- **API Reference** -- Doxygen-generated Python backend docs
- **Coverage Reports** -- Backend (pytest) and frontend (Vitest)
- **E2E Reports** -- Playwright test results

## CI/CD Pipeline

The GitLab CI/CD pipeline automates quality, security, and delivery:

| Stage    | Jobs                                            |
| -------- | ----------------------------------------------- |
| lint     | Ruff, mypy, ESLint, Prettier                    |
| test     | pytest (PostgreSQL service), Vitest              |
| security | Bandit SAST, pip-audit, npm audit, gitleaks      |
| build    | Docker image via Kaniko to GitLab Registry       |
| scan     | Trivy container vulnerability scanning           |
| e2e      | Playwright (manual trigger)                      |
| report   | Coverage badge generation                        |
| pages    | MkDocs + Doxygen + reports to GitLab Pages       |
| release  | GitLab Release with changelog on version tags    |

## Deployment

| Target                | Method                                |
| --------------------- | ------------------------------------- |
| Docker Compose        | `deploy/docker-compose.yml` (primary) |
| Kubernetes            | Helm chart in `deploy/helm/nexara/`   |
| unRAID                | Community Applications template       |
| Docs (GitHub Pages)   | <https://jmo-labs.github.io/nexara>   |

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
