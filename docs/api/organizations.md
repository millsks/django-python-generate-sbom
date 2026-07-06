# Organizations & Membership

Manage the organizations a user belongs to and their rosters. All endpoints
require [authentication](authentication.md). Endpoints marked **admin** require
the caller to be an admin of the active organization; otherwise they return
`403 not_admin`. Endpoints marked **global admin** require the caller to be a
global admin (a member of the system ADMIN org); otherwise they return
`403 not_global_admin`. Endpoints that need an active org return
`404 no_active_org` when the user has none.

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

Create a new organization with the caller as its admin. **Global admin only**
(Story 2.12) — a non-global-admin receives `403 not_global_admin`. The `slug` is
derived from `name` and made unique automatically (a numeric suffix is appended
on collision).

**Request body** — `{ "name": "Acme, Inc." }` (`name`, max 255 chars).

**Response `201 Created`** — `{ "slug": "acme", "name": "Acme, Inc." }`.

**Errors** — `403 not_global_admin` (caller is not a global admin),
`400 validation_error` (missing or too-long `name`).

!!! note "Global-admin provisioning"
    Every [global admin](#global-admin-management) is automatically added as an
    **admin** of the new org at creation time. This keeps global admins co-owners
    of every organization in the system.

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

List the active org's roster and whether the caller is an admin. **Admin only.**

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

**Errors** — `403 not_admin`.

## `POST /api/v1/orgs/members/`

Add an **already-registered** user to the active org by email. **Admin only.**
There is no account creation here — the person must have
[registered](authentication.md#post-apiv1authregister) first; an unknown email
is rejected rather than provisioned. To provision a brand-new account instead,
use [create-user](#post-apiv1orgsmemberscreate-user).

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

## `POST /api/v1/orgs/members/create-user/`

Create a **brand-new** user account and add it to the active org in one step
(Story 2.10). **Admin only.** Distinct from
[add-existing](#post-apiv1orgsmembers): this provisions a new account with an
admin-set temporary password (shared out of band — there is no email). Use it
when the person does not have an account yet.

**Request body**

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string (email) | Must not already be registered |
| `temp_password` | string | Temporary password, minimum 8 characters |

**Response `201 Created`** — `{ "user_id": 4, "email": "created@acme.com" }`.

**Errors**

| Status | Code | When |
| --- | --- | --- |
| `403` | `not_admin` | Caller is not an admin of the active org |
| `400` | `validation_error` | Missing/malformed `email` or too-short `temp_password` |
| `400` | `email_taken` | A user with that email already exists — add them as an existing member instead |

## `DELETE /api/v1/orgs/members/{user_id}/`

Remove a member from the active org. **Admin only.**

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `404 not_a_member`, `400` (membership error, e.g.
`last_admin` when removing the sole admin, or `global_admin_protected` when
removing a global admin from a single org).

## `POST /api/v1/orgs/promote-admin/`

Promote a member of the active org to **admin** (Story 2.16). **Admin only.**
This *adds* an admin — an org may have any number — and demotes no one. (It
replaces the old `transfer-admin`, which demoted the sole admin.) Idempotent if
the target is already an admin.

**Request body** — `{ "user_id": 2 }`.

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `400 validation_error` (missing/invalid
`user_id`), `404 not_a_member` (no such member of the org).

## `POST /api/v1/orgs/demote-admin/`

Demote an admin of the active org back to **member** (Story 2.20). **Admin
only.** The inverse of promote-admin; it changes the target's role in this org
only. Idempotent if the target is already a member.

**Request body** — `{ "user_id": 2 }`.

**Response `204 No Content`.**

**Errors** — `403 not_admin`, `400 validation_error`, `404 not_a_member`, and
`400` membership errors: `global_admin_protected` (a global admin must stay an
admin of every org) and `last_admin` (an org must keep at least one admin).

## `POST /api/v1/orgs/leave/`

Leave the active organization. A sole admin cannot leave.

**Response `204 No Content`.**

**Errors** — `404 no_active_org`, `400` (membership error).

---

## Global-admin management

The global-admin tier is the system **ADMIN** org (`Org.is_admin_org=True`): its
members are global admins, provisioned as an admin of every organization. These
endpoints are **global admin only** — any other caller receives
`403 not_global_admin` (Story 13.1).

### `GET /api/v1/admin/global-admins/`

List the current global admins.

**Response `200 OK`**

```json
{
  "global_admins": [
    { "user_id": 1, "email": "root@example.com" },
    { "user_id": 5, "email": "ops@example.com" }
  ]
}
```

**Errors** — `403 not_global_admin`.

### `POST /api/v1/admin/global-admins/`

Grant **global admin** to an **already-registered** user, looked up by email.
The target is added to the ADMIN org and back-filled as an **admin of every
existing (and future) organization**. There is no account creation — an unknown
email is rejected, mirroring [add-existing](#post-apiv1orgsmembers).

**Request body**

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string (email) | The existing user's email (case-insensitive) |

**Response `201 Created`** — `{ "user_id": 5, "email": "ops@example.com" }`.

**Errors** — `403 not_global_admin`, `400 validation_error` (missing/malformed
`email`), `400 no_such_user` (no registered user with that email).

### `DELETE /api/v1/admin/global-admins/{user_id}/`

Revoke a user's global-admin status. Removes them from the ADMIN org **and**
demotes them to `member` in every non-admin org. A per-org admin can re-promote
them later if needed.

**Response `204 No Content`.**

**Errors** — `403 not_global_admin`, `404 not_found` (no user with that id),
`400 last_global_admin` (cannot revoke the last remaining global admin — the
tier must never be left empty).
