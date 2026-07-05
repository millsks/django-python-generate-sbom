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

Create a new organization with the caller as its admin.

**Request body** — `{ "name": "Acme, Inc." }` (`name`, max 255 chars).

**Response `201 Created`** — `{ "slug": "acme", "name": "Acme, Inc." }`.

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

Add a member to the active org. **Admin only.**

**Request body**

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string (email) | The new member's email |
| `temp_password` | string | Minimum 8 characters |

**Response `201 Created`** — `{ "user_id": 3, "email": "new@acme.com" }`.

**Errors** — `403 not_admin`, `400 validation_error` (or a membership error code).

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
