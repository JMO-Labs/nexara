# Lists API

This page covers the REST endpoints for shared lists (`/api/v1/lists`). The
source is `backend/app/api/v1/lists.py` and the schemas in
`backend/app/schemas/list.py`. For the full generated schema, see the
[API reference](api-reference.md).

> **Note:** list templates (`/api/v1/list_templates`) are documented on their
> own page: [List templates API](list-templates-api.md).

## Conventions

- **Base path:** `/api/v1`. All bodies are JSON.
- **Auth:** every endpoint needs a JWT access token sent as
  `Authorization: Bearer <token>`. A missing or invalid token returns `401`.
- **Scope:** rows are scoped to the server's community. A list you cannot see
  returns `404`, not `403`, so its existence is not leaked.
- **Admins:** users with role `admin` or `owner` may update lists and manage
  members of lists they do not own.
- **Pagination:** list endpoints use keyset pagination. Pass the returned
  opaque `cursor` back to get the next page. `has_more` is `false` on the last
  page.
- **Visibility:** `community` (all members), `subgroup` (members of
  `subgroup_id`), `private` (owner only), `members` (explicit list members).

### Error envelope

Every error uses the standard envelope. `details` is optional and only present
when there is extra context (validation errors, slot counts).

```json
{
  "error": {
    "code": "NO_SLOTS",
    "message": "Not enough open slots",
    "details": { "remaining": 1 }
  }
}
```

| Status | `code` | When |
|--------|--------|------|
| 401 | `AUTHENTICATION_ERROR` | Missing, expired or invalid token |
| 403 | `AUTHORIZATION_ERROR` | Visible, but you may not modify it |
| 404 | `NOT_FOUND` | Missing, deleted or not visible to you |
| 409 | `CONFLICT` | Already a member |
| 409 | `SIGNUP_NOT_ENABLED` | Item does not accept signups |
| 409 | `ALREADY_CLAIMED` | You already signed up for this item |
| 409 | `NO_SLOTS` | Not enough open slots (`details.remaining`) |
| 422 | `VALIDATION_ERROR` | Body/query validation failed (`details` maps field to message) |
| 422 | `FIELD_NOT_FOUND` | `field_key` matches no checkbox field |

Validation error example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": { "body.title": "String should have at least 1 character" }
  }
}
```

### List object

Returned by list endpoints (abbreviated as `List` below).

```json
{
  "id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10",
  "title": "Camping trip packing",
  "description": "Bring your own sleeping bag",
  "visibility": "community",
  "owner_id": "2b0d6a1c-4f3e-4f63-8a6e-3f1b9d2c7e44",
  "community_id": "00000000-0000-0000-0000-000000000001",
  "template_id": null,
  "subgroup_id": null,
  "status": "active",
  "expires_at": null,
  "color": null,
  "item_count": 12,
  "completed_count": 4,
  "signup_count": 3,
  "created_at": "2026-11-01T10:00:00Z",
  "updated_at": "2026-11-02T08:30:00Z",
  "field_schema": [
    { "key": "name", "type": "text", "label": "Item" },
    { "key": "done", "type": "checkbox", "label": "Packed", "config": { "completion_mode": "shared" } }
  ]
}
```

### Item object

Abbreviated as `ListItem` below.

```json
{
  "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01",
  "position": 0,
  "values": { "name": "Tent" },
  "due_at": null,
  "completed": false,
  "completed_by": null,
  "completed_at": null,
  "lat": null,
  "lon": null,
  "signup_quantity_needed": 2
}
```

## Lists

### `GET /api/v1/lists`

Keyset page of lists visible to the caller.

**Auth:** Bearer token. **Query:** `cursor` (string, optional), `limit` (1-100, default 20).

**Response `200`:**

```json
{
  "lists": [ { "id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10", "title": "Camping trip packing", "...": "List fields" } ],
  "pagination": { "cursor": "eyJ2IjoiMjAyNi0xMS0wMSJ9", "has_more": true }
}
```

### `POST /api/v1/lists`

Create a list owned by the caller. `subgroup_id` is required when
`visibility` is `subgroup`.

**Auth:** Bearer token.

**Request:**

```json
{
  "title": "Camping trip packing",
  "description": "Bring your own sleeping bag",
  "visibility": "community",
  "subgroup_id": null,
  "field_schema": [ { "key": "name", "type": "text", "label": "Item" } ]
}
```

**Response `201`:** a `List` object.

```json
{ "id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10", "title": "Camping trip packing", "visibility": "community", "status": "active", "item_count": 0 }
```

**Errors:** `422 VALIDATION_ERROR` (empty title, invalid visibility, missing `subgroup_id`, invalid field schema).

### `GET /api/v1/lists/{list_id}`

Fetch a visible list.

**Auth:** Bearer token.

**Response `200`:** a `List` object.

```json
{ "id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10", "title": "Camping trip packing", "visibility": "community" }
```

**Errors:** `404 NOT_FOUND`.

### `PUT /api/v1/lists/{list_id}`

Partial update. Only fields you send change. Owner or admin only.

**Auth:** Bearer token (owner or admin).

**Request:**

```json
{ "title": "Camping trip 2027", "description": null, "color": "#7c3aed", "expires_at": "2027-06-30T00:00:00Z" }
```

**Response `200`:** the updated `List` object.

```json
{ "id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10", "title": "Camping trip 2027", "expires_at": "2027-06-30T00:00:00Z" }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`, `422 VALIDATION_ERROR`.

### `DELETE /api/v1/lists/{list_id}`

Soft-delete a list. Owner only.

**Auth:** Bearer token (owner).

**Response:** `204 No Content`.

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`.

### `POST /api/v1/lists/{list_id}/archive`

Archive a list (sets `status` to `archived`). No request body.

**Auth:** Bearer token (owner or community admin).

**Response `200`:** the updated list object.

```json
{ "id": "3f1c2a9e-7b4d-4c1a-9e2f-0a1b2c3d4e5f", "title": "Camping gear", "status": "archived" }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`.

## Items

### `GET /api/v1/lists/{list_id}/items`

Keyset page of a list's items.

**Auth:** Bearer token (list must be visible). **Query:** `cursor`, `limit`
(1-200, default 50), `sort_by` (`position` or `created_at`, default `position`).

**Response `200`:**

```json
{
  "items": [ { "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "position": 0, "values": { "name": "Tent" }, "completed": false } ],
  "pagination": { "cursor": null, "has_more": false }
}
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`, `422 VALIDATION_ERROR` (bad `sort_by` or cursor).

### `POST /api/v1/lists/{list_id}/items`

Add an item. `values` keys must match the list's `field_schema`. Owner only.

**Auth:** Bearer token (list owner).

**Request:**

```json
{ "position": 0, "values": { "name": "Tent" } }
```

**Response `201`:** a `ListItem` object.

```json
{ "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "position": 0, "values": { "name": "Tent" }, "completed": false }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`, `422 VALIDATION_ERROR` (unknown fields: `details.fields`; bad value: `details.field`).

### `PUT /api/v1/lists/{list_id}/items/{item_id}`

Replace an item's values. Owner only.

**Auth:** Bearer token (list owner).

**Request:**

```json
{ "values": { "name": "Tent (4-person)" } }
```

**Response `200`:** the updated `ListItem` object.

```json
{ "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "position": 0, "values": { "name": "Tent (4-person)" } }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND` (item not in this list), `422 VALIDATION_ERROR`.

### `DELETE /api/v1/lists/{list_id}/items/{item_id}`

Soft-delete an item. Owner only.

**Auth:** Bearer token (list owner).

**Response:** `204 No Content`.

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`.

### `POST /api/v1/lists/{list_id}/items/{item_id}/complete`

Mark an item complete. In `shared` mode it completes for everyone; in
`per_user` mode only for the caller. No body.

**Auth:** Bearer token (list must be visible). **Query:** `field_key`
(optional; defaults to the first checkbox field).

**Response `200`:** the updated `ListItem` object.

```json
{ "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "completed": true, "completed_by": "2b0d6a1c-4f3e-4f63-8a6e-3f1b9d2c7e44", "completed_at": "2026-11-14T09:12:00Z" }
```

**Errors:** `404 NOT_FOUND`, `422 FIELD_NOT_FOUND`.

### `POST /api/v1/lists/{list_id}/items/{item_id}/uncomplete`

Reverse a completion. Same query and rules as `complete`. No body.

**Auth:** Bearer token (list must be visible).

**Response `200`:** the updated `ListItem` object.

```json
{ "id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "completed": false, "completed_by": null, "completed_at": null }
```

**Errors:** `404 NOT_FOUND`, `422 FIELD_NOT_FOUND`.

## Members

Explicit members apply to lists with `visibility: "members"`.

### `GET /api/v1/lists/{list_id}/members`

Members of a visible list.

**Auth:** Bearer token (list must be visible).

**Response `200`:**

```json
[
  {
    "list_id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10",
    "user_id": "c4e8f0a2-7d3b-4b1e-9f6a-1e2d3c4b5a67",
    "role": "editor",
    "share_personal": false,
    "added_at": "2026-11-03T12:00:00Z"
  }
]
```

**Errors:** `404 NOT_FOUND`.

### `POST /api/v1/lists/{list_id}/members`

Add a member. Owner or admin only. `role` is `viewer` (default) or `editor`.

**Auth:** Bearer token (owner or admin).

**Request:**

```json
{ "user_id": "c4e8f0a2-7d3b-4b1e-9f6a-1e2d3c4b5a67", "role": "editor" }
```

**Response `201`:** the new member.

```json
{ "list_id": "6f1c2a1e-1b7e-4a5e-9d1a-0c3f0e6b2a10", "user_id": "c4e8f0a2-7d3b-4b1e-9f6a-1e2d3c4b5a67", "role": "editor", "share_personal": false, "added_at": "2026-11-14T09:00:00Z" }
```

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND`, `409 CONFLICT` (already a member), `422 VALIDATION_ERROR` (list does not use explicit members).

### `DELETE /api/v1/lists/{list_id}/members/{member_id}`

Remove a member. `member_id` is the member's user ID.

**Auth:** Bearer token (owner or admin).

**Response:** `204 No Content`.

**Errors:** `403 AUTHORIZATION_ERROR`, `404 NOT_FOUND` (member not found).

## Signups

Signups let members claim slots on an item (for example "bring 2 chairs").

### `GET /api/v1/lists/{list_id}/items/{item_id}/signups`

Claims on an item.

**Auth:** Bearer token (list must be visible).

**Response `200`:**

```json
[
  {
    "item_id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01",
    "user_id": "c4e8f0a2-7d3b-4b1e-9f6a-1e2d3c4b5a67",
    "quantity": 1,
    "note": "Bringing the blue one",
    "claimed_at": "2026-11-10T18:00:00Z"
  }
]
```

**Errors:** `404 NOT_FOUND`.

### `POST /api/v1/lists/{list_id}/items/{item_id}/signups`

Claim slots on an item.

**Auth:** Bearer token (list must be visible).

**Request:**

```json
{ "quantity": 1, "note": "Bringing the blue one" }
```

**Response `201`:** the new claim.

```json
{ "item_id": "9a7e1d40-3c2b-4e0f-8b8e-5d1c7f2a9b01", "user_id": "c4e8f0a2-7d3b-4b1e-9f6a-1e2d3c4b5a67", "quantity": 1, "note": "Bringing the blue one", "claimed_at": "2026-11-14T09:00:00Z" }
```

**Errors:** `404 NOT_FOUND`, `409 SIGNUP_NOT_ENABLED`, `409 ALREADY_CLAIMED`, `409 NO_SLOTS`, `422 VALIDATION_ERROR` (`quantity` < 1).

### `DELETE /api/v1/lists/{list_id}/items/{item_id}/signups`

Release the caller's claim on an item.

**Auth:** Bearer token (list must be visible).

**Response:** `204 No Content`.

**Errors:** `404 NOT_FOUND` (item or claim not found).
