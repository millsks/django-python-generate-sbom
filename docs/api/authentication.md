# Authentication

The API supports two authentication schemes. Every endpoint requires one of
them, except registration and login (which are open by definition).

## Schemes

### Session (browser / web UI)

The single-page app authenticates with a Django session cookie. Call
[`POST /api/v1/auth/login/`](#post-apiv1authlogin) to establish the session;
the response sets a `sessionid` cookie and a `csrftoken` cookie. Subsequent
state-changing requests (`POST`, `DELETE`, …) must echo the CSRF token in an
`X-CSRFToken` header. With session auth, the **active organization** is the one
stored in the session (set at login and changed via
[`POST /api/v1/orgs/switch/`](organizations.md#post-apiv1orgsswitch)).

### API key (programmatic)

Send an organization API key in the `Authorization` header:

```http
Authorization: Api-Key <your-key>
```

Create keys from [API Keys](api-keys.md). With API-key auth the **active
organization** is fixed to the key's own organization — there is nothing to
switch. Revoked or unknown keys return `401` with code `invalid_api_key`.

The permission layer accepts *either* a valid session user *or* a valid API
key; requests with neither are rejected.

---

## `POST /api/v1/auth/register/`

Create a new user account. **No authentication.** A new user starts with **no
organizations** — registration does not create a personal org, so `org` is
always `null`. A user joins an org by being
[added as a member](organizations.md#post-apiv1orgsmembers) by an admin, or by
[creating one](organizations.md#post-apiv1orgscreate).

**Request body**

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string (email) | Must not already be registered |
| `password` | string | Minimum 8 characters |

**Response `201 Created`**

```json
{
  "user": { "id": 1, "email": "you@example.com" },
  "org": null
}
```

**Errors** — `400 validation_error` (invalid input or email already in use).

---

## `POST /api/v1/auth/login/`

Exchange credentials for a session and select the user's active org. **No
authentication.** Sets `sessionid` and `csrftoken` cookies.

**Request body**

| Field | Type |
| --- | --- |
| `email` | string (email) |
| `password` | string |

**Response `200 OK`** — `org` is `null` when the user belongs to no org.

```json
{ "org": { "slug": "acme", "name": "Acme, Inc." } }
```

**Errors** — `400 invalid_credentials` (malformed request),
`401 invalid_credentials` (wrong email or password).

---

## `POST /api/v1/auth/logout/`

Invalidate the current session. **Authentication required.**

**Response `204 No Content`.**

---

## `GET /api/v1/auth/me/`

Return the currently authenticated user's identity and role flags.
**Authentication required.** This is the SPA's identity signal — a logged-in user
with **zero organizations** is still authenticated and gets a `200` here. The two
boolean flags are the client's single source of truth for gating admin-only nav,
routes, and affordances, so it never has to probe an admin-only endpoint to learn
its role.

**Response `200 OK`**

```json
{
  "id": 1,
  "email": "you@example.com",
  "is_admin": false,
  "is_global_admin": false
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | integer | The user's id |
| `email` | string | The user's email (login identifier) |
| `is_admin` | boolean | `true` when the user is an admin of the **active** organization (Story 2.6) |
| `is_global_admin` | boolean | `true` when the user is a global admin — a member of the system ADMIN org (Story 2.12) |

**Errors** — `401` when the request carries no valid session or API key. (The
API accepts either scheme, and its API-key challenge sets a `WWW-Authenticate`
header, so an anonymous request renders as `401`, not `403`.)
