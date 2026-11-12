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

## Static reference

A searchable single-page reference, generated from the OpenAPI schema with
redoc-cli, is published with this site: [Open the API reference](api-reference.html).
It lists every endpoint grouped by resource, with method and path, summary,
request and response schemas, authentication requirements, and error codes.

To regenerate it locally, run `scripts/generate-api-ref.sh`. By default it
dumps the schema from the FastAPI app; set `OPENAPI_URL` (for example
`http://localhost:8000/openapi.json`) to read it from a running server. The
HTML output is not committed.

## Base URL and authentication

The API is REST over JSON. The base URL for a deployment is
`https://api.nexara.example/v1` (substitute your own host). Authenticate with a
JWT access token sent as `Authorization: Bearer <token>`. Obtain tokens from the
auth endpoints and refresh them before they expire. Requests without a valid
token receive a `401` in the standard error envelope.

## Examples

List posts:

```bash
curl -H "Authorization: Bearer $TOKEN" https://api.nexara.example/v1/posts
```

`GET /posts` returns the posts visible to the caller, newest first.

Create a post:

```bash
curl -X POST https://api.nexara.example/v1/posts \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"body": "Hello everyone", "visibility": "community"}'
```

`POST /posts` returns the created post. Use `visibility` values `community`,
`subgroup` (with `subgroup_id`), or `private`.

Update a post:

```bash
curl -X PATCH https://api.nexara.example/v1/posts/123 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"body": "Edited text"}'
```

`PATCH /posts/{id}` changes only the fields you send. Only the author, or a
moderator, may edit a post.

Delete a post:

```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" https://api.nexara.example/v1/posts/123
```

`DELETE /posts/{id}` soft-deletes the post.

## Errors

Failures use the envelope `{ "error": { "code", "message", "details" } }`.
Typical codes are `not_found` (404), `forbidden` (403), and validation errors
(422).

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
