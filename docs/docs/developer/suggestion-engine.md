# Suggestion Engine

AI-generated conversation prompts and poll ideas that admins review before use.
Requires `AI_PROVIDER` to be configured; without it, generation is a no-op.

## Workflow

1. **Generate** — an admin calls `POST /api/v1/admin/suggestions/generate`.
   - `type=prompt`: uses the last 10 community posts, top 5 interests and next 5
     events; stores up to 5 prompts (max 100 chars each) as `{"text": "..."}`.
   - `type=poll&topic=...`: stores one poll as
     `{"question": "...", "options": [4 strings], "topic": "..."}`.
2. **Review** — `GET /api/v1/admin/suggestions` lists pending items.
3. **Decide** — `approve` sets `approved_at`/`approved_by`; `reject` sets `rejected_at`.
   A suggestion can be decided once (second attempt returns `409`).

Approval records the decision only; the admin UI posts the approved content
through the normal post/poll endpoints.

If the AI call fails, returns malformed output, or no context exists, nothing is
stored and the endpoint still returns `200` with `{"created": 0}`.

## Endpoints (admin role required; others get `403`)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/admin/suggestions?type=prompt&limit=10&offset=0` | `type` is `prompt` or `poll` (optional); `limit` 1-100 |
| POST | `/api/v1/admin/suggestions/generate?type=prompt` | `{"created": n}`; poll needs `topic` (else `422`) |
| POST | `/api/v1/admin/suggestions/{id}/approve` | Suggestion; `404` unknown, `409` already decided |
| POST | `/api/v1/admin/suggestions/{id}/reject` | Suggestion; `404` unknown, `409` already decided |

Suggestion shape:

```json
{
  "id": "uuid", "type": "prompt", "content": {"text": "What did you cook this week?"},
  "suggested_by": "ai", "approved_at": null, "approved_by": null,
  "rejected_at": null, "created_at": "2026-01-01T00:00:00Z"
}
```
