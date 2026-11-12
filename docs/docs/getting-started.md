# Getting Started

This guide walks you through setting up a Nexara development environment from
a fresh clone to a running app.

## Prerequisites

| Tool       | Version | Purpose                        |
| ---------- | ------- | ------------------------------ |
| Node.js    | 20+     | Frontend build and dev server  |
| Python     | 3.11+   | Backend runtime                |
| uv         | latest  | Python package/venv management |
| PostgreSQL | 16      | Database (real DB, no SQLite)  |
| Valkey     | 7+      | Cache, pub/sub, Celery broker  |

## Clone the Repository

```bash
git clone https://github.com/JMO-Labs/nexara.git && cd nexara
```

## Backend Setup

```bash
cd backend
uv venv .venv && source .venv/bin/activate && uv sync
```

## Frontend Setup

```bash
cd frontend
npm install
```

## Database Setup

Create a PostgreSQL 16 database and make sure Valkey is running. For a quick
local database with Docker:

```bash
docker run -d --name nexara-db \
  -e POSTGRES_DB=nexara -e POSTGRES_USER=nexara \
  -e POSTGRES_PASSWORD=localdev -p 5432:5432 postgres:16-alpine
```

Then run the migrations:

```bash
cd backend
alembic upgrade head
```

## Run the Dev Servers

Use two terminals.

```bash
# Terminal 1 - backend
cd backend && uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 - frontend
cd frontend && npm run dev
```

Open <http://localhost:3000/app> in your browser.

## Running Tests

```bash
cd backend && pytest --cov=app --cov-report=html -v
cd frontend && npm test
```

## Troubleshooting

- **Port already in use** (`8000` or `3000`): stop the other process, or pass
  another port, e.g. `uvicorn app.main:app --reload --port 8001`.
- **Migration failed / cannot connect**: confirm PostgreSQL is up, the
  database exists, and the connection settings in your environment match.
  Re-run `alembic upgrade head` after fixing.
- **Multiple Alembic heads**: run `alembic heads` and ensure a single head
  before upgrading.
- **Backend tests error on connect**: tests need a real PostgreSQL; SQLite is
  not supported.
- **`uv: command not found`**: install uv from the official docs, then repeat
  the backend setup.

## Next Steps

- Read the [Development Guide](development.md) for architecture and conventions
- Read the [Deployment Guide](deployment.md) for production setup
