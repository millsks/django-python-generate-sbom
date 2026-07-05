# Organizations & Membership

Manage the organizations a user belongs to and their rosters. All endpoints
require [authentication](authentication.md). Endpoints marked **admin** require
the caller to be an admin of the active organization; otherwise they return
`403 not_admin`. Endpoints that need an active org return `404 no_active_org`
when the user has none.

## `GET /api/v1/orgs/`

List the organizations the caller belongs to, flagging the active one.

**Response `200 OK`**

```json
[
  { "slug": "acme", "name": "Acme, Inc.", "active": true },
  { "slug": "side-project", "name": "Side Project", "active": false }
]
```

## `POST /api/v1/orgs/create/`

Create a new organization with the caller as its admin. The `slug` is derived
from `name` and made unique automatically (a numeric suffix is appended on
collision).

**Request body** — `{ "name": "Acme, Inc." }` (`name`, max 255 chars).

**Response `201 Created`** — `{ "slug": "acme", "name": "Acme, Inc." }`.

**Errors** — `400 validation_error` (missing or too-long `name`).

!!! note "Global-admin provisioning"
    Every [global admin](#post-apiv1adminglobal-admins) is automatically added
    as an **admin** of the new org at creation time. This keeps global admins
    co-owners of every organization in the system.

## `POST /api/v1/orgs/switch/`

Set the caller's active organization (session auth).

**Request body** — `{ "slug": "acme" }`.

**Response `200 OK`** — `{ "slug": "acme", "name": "Acme, Inc." }`.

**Errors** — `403 not_a_member` if the caller does not belong to that org.

## `GET /api/v1/orgs/me/`

Return the current active organization.

**Response `200 OK`** — `{ "slug": "acme", "name": "Acme, Inc." }`.

**Errors** — `404 no_active_org`.

## `GET /api/v1/orgs/members/`

List the active org's roster and whether the caller is an admin.

**Response `200 OK`**

```json
{
  "members": [
    { "user_id": 1, "email": "admin@acme.com", "role": "admin", "joined_at": "2026-01-02T10:00:00+00:00" },
    { "user_id": 2, "email": "dev@acme.com", "role": "member", "joined_at": "2026-01-03T09:00:00+00:00" }
  ],
  "is_admin": true
}
```

**Errors** — `404 no_active_org`.

## `POST /api/v1/orgs/members/`

Add an **already-registered** user to the active org by email. **Admin only.**
There is no account creation here — the person must have
[registered](authentication.md#post-apiv1authregister) first; an unknown email
is rejected rather than provisioned.

**Request body**

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string (email) | The existing user's email (case-insensitive) |

**Response `201 Created`** — `{ "user_id": 3, "email": "new@acme.com" }`.

**Errors**

| Status | Code | When |
| --- | --- | --- |
| `403` | `not_admin` | Caller is not an admin of the active org |
| `400` | `validation_error` | Missing or malformed `email` |
| `400` | `no_such_user` | No registered user has that email |
| `400` | `already_member` | That user already belongs to the org |

## `DELETE /api/v1/orgs/members/{user_id}/`

Remove a member from the active org. **Admin only.**

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `404 not_a_member`, `400` (membership error, e.g. removing the sole admin).

## `POST /api/v1/orgs/transfer-admin/`

Transfer the admin role to another member. **Admin only.**

**Request body** — `{ "user_id": 2 }`.

**Response `200 OK`.**

**Errors** — `403 not_admin`, `404 not_a_member`, `400` (membership error).

## `POST /api/v1/orgs/leave/`

Leave the active organization. A sole admin cannot leave.

**Response `204 No Content`.**

**Errors** — `404 no_active_org`, `400` (membership error).

## `POST /api/v1/admin/global-admins/`

Grant **global admin** to another user. **Global admins only** — the caller must
already be a global admin. The target is added to the system ADMIN org and
back-filled as an **admin of every existing (and future) organization**.

**Request body** — `{ "user_id": 2 }`.

**Response `201 Created`** — `{ "user_id": 2, "email": "new-admin@acme.com" }`.

**Errors** — `403 not_global_admin` (caller is not a global admin),
`400 validation_error` (missing or invalid `user_id`), `404 not_found` (no user
with that id).
