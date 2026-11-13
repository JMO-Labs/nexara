# Getting Started

Set up a local Nexara development environment in a few minutes.

## Prerequisites

| Tool       | Version | Purpose                        |
| ---------- | ------- | ------------------------------ |
| Node.js    | 20+     | Frontend (Next.js 16)          |
| Python     | 3.12+   | Backend (FastAPI)              |
| uv         | latest  | Python venv/package management |
| PostgreSQL | 16      | Database                       |
| Valkey     | latest  | Cache, pub/sub, Celery broker  |

## Clone

```bash
git clone https://github.com/JMO-Labs/nexara.git && cd nexara
```

## Backend Setup

Run every command on this page from the repo root (`nexara/`). Commands that
enter `backend/` or `frontend/` either use a `( ... )` subshell or `cd ..` back,
so the blocks work when pasted top to bottom.

```bash
cd backend && uv venv .venv && source .venv/bin/activate && uv sync && cd ..
```

## Frontend Setup

```bash
(cd frontend && npm install)
```

## Database

Start PostgreSQL 16 and Valkey locally (or via Docker), then migrate:

```bash
docker run -d --name nexara-db \
  -e POSTGRES_DB=nexara -e POSTGRES_USER=nexara \
  -e POSTGRES_PASSWORD=localdev -p 5432:5432 postgres:16-alpine
docker run -d --name nexara-valkey -p 6379:6379 valkey/valkey:8-alpine
```

```bash
(cd backend && alembic upgrade head)
```

## Run the Dev Servers

Use two terminals, each opened at the repo root.

```bash
# Terminal 1 - backend
(cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000)
```

```bash
# Terminal 2 - frontend
(cd frontend && npm run dev)
```

Open <http://localhost:3000/app> in your browser.

## Run the Tests

```bash
(cd backend && pytest --cov=app --cov-report=html -v)
(cd frontend && npm test)
```

Backend commands (`alembic`, `pytest`) expect the venv activated in Backend
Setup. Backend tests need a real PostgreSQL instance (no SQLite).

## Troubleshooting

- **Port already in use** -- another process holds `8000` or `3000`. Stop it,
  or pass a different port (`--port 8001`, `npm run dev -- -p 3001`).
- **Migration failed** -- confirm PostgreSQL is running and the database URL in
  your environment is correct. Run `alembic heads` to check there is a single
  head, then `alembic upgrade head` again.
- **Connection refused (Valkey/Redis)** -- start Valkey on port `6379`.
- **`uv: command not found`** -- install uv, then re-run `uv sync`.
- **Frontend cannot reach the API** -- make sure the backend is on port `8000`
  and that `ALLOWED_ORIGINS` includes `http://localhost:3000`.

## Running the Full Stack

```bash
(cd deploy && cp .env.example .env && docker compose up -d)
```

The app is available through the proxy on `http://localhost:8080`.

## Next Steps

- [Development Guide](development.md) for architecture and conventions
- [Deployment Guide](deployment/deployment-guide.md) for production setup
