# API Keys

Organization API keys authenticate programmatic access (see
[Authentication](authentication.md)). All endpoints require
[authentication](authentication.md) and operate on the active organization
(`404 no_active_org` when there is none). Creating and revoking keys is
**admin only**.

## `GET /api/v1/keys/`

List the active org's non-revoked keys. The secret is never returned — only its
short `prefix`.

**Response `200 OK`**

```json
[
  {
    "id": 7,
    "name": "CI pipeline",
    "prefix": "abcd1234",
    "created_at": "2026-02-01T12:00:00+00:00",
    "last_used_at": "2026-03-15T08:30:00+00:00"
  }
]
```

`last_used_at` is `null` until the key is first used.

**Errors** — `404 no_active_org`.

## `POST /api/v1/keys/`

Create a new API key. **Admin only.** The full plaintext key is returned
**exactly once** in the `key` field — store it now; it cannot be retrieved
again.

**Request body** — `{ "name": "CI pipeline" }` (`name`, max 100 chars).

**Response `201 Created`**

```json
{ "id": 7, "name": "CI pipeline", "prefix": "abcd1234", "key": "abcd1234.xxxxxxxxxxxxxxxxxxxx" }
```

**Errors** — `403 not_admin`, `400 validation_error`.

## `DELETE /api/v1/keys/{key_id}/`

Revoke (soft-delete) an API key. **Admin only.** The key stops authenticating
immediately.

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `404 not_found` (no active key with that id in the caller's org).
