# Getting Started

This guide walks you through setting up a Nexara development environment.

## Prerequisites

| Tool     | Version | Purpose                         |
| -------- | ------- | ------------------------------- |
| Python   | 3.12+   | Backend runtime                 |
| uv       | latest  | Python package/venv management  |
| Node.js  | 20+     | Frontend build and dev server   |
| Docker   | 24+     | Container builds and services   |
| PostgreSQL | 16+   | Database (via Docker or local)  |

## Clone the Repository

```bash
git clone https://gitlab.com/<namespace>/nexara.git
cd nexara
```

## Backend Setup

```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv sync
```

Run the backend development server:

```bash
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
```

Run the frontend development server:

```bash
npm run dev
```

## Database Setup

Start PostgreSQL via Docker:

```bash
docker run -d \
  --name nexara-db \
  -e POSTGRES_DB=nexara \
  -e POSTGRES_USER=nexara \
  -e POSTGRES_PASSWORD=localdev \
  -p 5432:5432 \
  postgres:16-alpine
```

Run database migrations:

```bash
cd backend
alembic upgrade head
```

## Running Tests

```bash
# Backend tests
cd backend
pytest --cov=app -v

# Frontend tests
cd frontend
npx vitest run --coverage
```

## Next Steps

- Read the [Development Guide](development.md) for architecture and conventions
- Read the [Deployment Guide](deployment.md) for production setup
