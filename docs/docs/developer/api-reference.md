# API Reference

Nexara exposes a versioned REST API under `/api/v1/`, plus Server-Sent Events
and WebSocket endpoints for realtime updates. This page explains where to find
the details.

## Interactive documentation

When the backend is running, FastAPI serves generated OpenAPI documentation:

- Swagger UI at `/docs`
- ReDoc at `/redoc`
- The raw schema at `/openapi.json`

These always match the running code and are the best source for request and
response schemas.

## Source documentation

The Doxygen-generated reference for the source code is published with this site
under [API Docs](../../api/). Coverage reports are published alongside it.

## Conventions

- All routes live in `backend/app/api/v1/`, one module per resource.
- Errors use a single envelope: `{ "error": { "code", "message", "details" } }`.
- Requests are scoped to the caller's community automatically.
- Realtime streams are in `api/v1/sse.py` and `api/v1/ws.py`.

See the [Architecture](architecture.md) page for how requests flow through the
service and repository layers.
