# List templates API

Templates are reusable list blueprints, served under `/api/v1/list_templates`.
The source is `backend/app/api/v1/list_templates.py` and the schemas in
`backend/app/schemas/list_template.py`. Auth, scope and the error envelope
follow the [Lists API conventions](lists-api.md#conventions): every endpoint
needs `Authorization: Bearer <token>`.

## Endpoints

### `GET /api/v1/list_templates`

Keyset page of templates visible to the caller (their own, shared and system templates).
Note the pagination fields sit at the top level here.

**Auth:** Bearer token. **Query:** `cursor`, `limit` (1-100, default 20).

**Response `200`:**

```json
{
  "templates": [
    {
      "id": "1d2c3b4a-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Potluck",
      "category": "events",
      "icon": "utensils",
      "color": null,
      "cover_media_id": null,
      "is_shared": true,
      "created_at": "2026-10-01T10:00:00Z",
      "updated_at": "2026-10-01T10:00:00Z",
      "fields": [ { "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "key": "dish", "label": "Dish", "type_key": "text", "required": true, "position": 0, "config": {} } ],
      "items": [ { "id": "0f1e2d3c-4b5a-4968-8778-695a4b3c2d1e", "position": 0, "values": { "dish": "Salad" } } ]
    }
  ],
  "cursor": null,
  "has_more": false
}
```

### `POST /api/v1/list_templates`

Create a template. Field `key` must match `^[a-z0-9_]+$` (max 64 chars).

**Auth:** Bearer token.

**Request:**

```json
{
  "name": "Potluck",
  "description": "Who brings what",
  "category": "events",
  "icon": "utensils",
  "color": null,
  "is_shared": true,
  "fields": [ { "key": "dish", "label": "Dish", "type_key": "text", "required": true, "position": 0, "config": {} } ],
  "items": [ { "position": 0, "values": { "dish": "Salad" } } ]
}
```

**Response `201`:** the template object.

```json
{ "id": "1d2c3b4a-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "name": "Potluck", "is_shared": true, "fields": [], "items": [] }
```

**Errors:** `422 VALIDATION_ERROR`.

### `GET /api/v1/list_templates/{template_id}`

Fetch a visible template.

**Auth:** Bearer token.

**Response `200`:** the template object.

```json
{ "id": "1d2c3b4a-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "name": "Potluck", "is_shared": true }
```

**Errors:** `404 NOT_FOUND`.

### `PUT /api/v1/list_templates/{template_id}`

Partial update. When `fields` or `items` is sent, it replaces the existing set.
Author only.

**Auth:** Bearer token (author).

**Request:**

```json
{ "name": "Summer potluck", "is_shared": false }
```

**Response `200`:** the updated template object.

```json
{ "id": "1d2c3b4a-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "name": "Summer potluck", "is_shared": false }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`, `422 VALIDATION_ERROR`.

### `DELETE /api/v1/list_templates/{template_id}`

Soft-delete a template. Author only.

**Auth:** Bearer token (author).

**Response:** `204 No Content`.

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`.

### `POST /api/v1/list_templates/{template_id}/clone`

Create a new list from a template. `visibility` is `community`, `subgroup` or
`private` (default). `title` defaults to the template name.

**Auth:** Bearer token (template must be visible).

**Request:**

```json
{ "title": "Potluck - Dec 12", "visibility": "community", "include_items": true }
```

**Response `201`:** a `List` object.

```json
{ "id": "5b4a3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d", "title": "Potluck - Dec 12", "template_id": "1d2c3b4a-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "visibility": "community" }
```

**Errors:** `404 NOT_FOUND`, `422 VALIDATION_ERROR`.
