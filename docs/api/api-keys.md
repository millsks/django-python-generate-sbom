# API Keys

Organization API keys select the organization a programmatic caller acts as (see
[Authentication](authentication.md)). All endpoints here operate on the active
organization.

!!! warning "The gates described below are not enforced"

    Story 21.24 removed the app's authentication, so **every endpoint on this page is open
    to an unauthenticated caller** — see [Authentication](authentication.md). The
    admin markers are kept because they record the authorization each endpoint
    is *meant* to carry, and Epics 17-18 restore that decision from host-supplied OIDC group
    claims at the same seam. Until then, treat them as intent, not protection, and deploy
    only on a trusted network.

    One consequence is worth stating plainly: `403 not_admin` is still returned, but **only
    when the deployment has no organization at all** — the caller is not being refused for
    lack of privilege.


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

Create a new API key. **Admin-scoped** (see the notice above). The full plaintext key is returned
**exactly once** in the `key` field — store it now; it cannot be retrieved
again.

**Request body** — `{ "name": "CI pipeline" }` (`name`, max 100 chars).

**Response `201 Created`**

```json
{ "id": 7, "name": "CI pipeline", "prefix": "abcd1234", "key": "abcd1234.xxxxxxxxxxxxxxxxxxxx" }
```

**Errors** — `403 not_admin`, `400 validation_error`.

## `DELETE /api/v1/keys/{key_id}/`

Revoke (soft-delete) an API key. **Admin-scoped** (see the notice above). The key stops authenticating
immediately.

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `404 not_found` (no active key with that id in the caller's org).
