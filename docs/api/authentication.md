# Authentication

!!! warning "The API does not require authentication"

    Story 21.24 removed the app's own authentication. **Every `/api/v1/` endpoint is open
    to an unauthenticated caller**, who acts as the deployment's default organization.
    Identity is intended to come from the host platform via OIDC and group claims; until
    that lands, deploy only on a trusted network.

    The API-key scheme below is **retained and still meaningful**: a caller who presents a
    key is pinned to that key's organization instead of the default one. It is now a way to
    select a tenant, not a way to gain access.

## Schemes

### No credentials (the default)

Send no `Authorization` header and no session cookie. The request is served, acting as the
organization named by `INVENTORY_DEFAULT_ORG_SLUG` (seeded on first migrate).

### API key (programmatic, selects the organization)

Send an organization API key in the `Authorization` header:

```http
Authorization: Api-Key <your-key>
```

Create keys from [API Keys](api-keys.md). With API-key auth the **active organization** is
fixed to the key's own organization — there is nothing to switch. Revoked or unknown keys
return `401` with code `invalid_api_key`.

### Session (Django admin only)

`django.contrib.admin` keeps its own login at `/admin/`. A request carrying that session
resolves its organization from the session, and state-changing requests must echo the CSRF
token in an `X-CSRFToken` header. **CSRF protection was not removed** with the login
requirement.

---

## Removed endpoints

`POST /api/v1/auth/register/`, `POST /api/v1/auth/login/`, and `POST /api/v1/auth/logout/`
were **deleted** by Story 21.24 along with the rest of the app's authentication. They
return `404`. They are listed here rather than silently dropped so a reader working from an
older copy of this page knows the endpoints are gone by design.

---

## `GET /api/v1/auth/me/`

Return the caller's identity and capability flags. **No authentication required** — it is
retained for clients that still call it, and reports a **null identity** for the ordinary
anonymous caller rather than refusing.

**Response `200 OK`** — anonymous caller (the usual case):

```json
{
  "id": null,
  "email": null,
  "is_admin": true,
  "is_global_admin": true
}
```

A request carrying a Django-admin session reports that user instead.

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | integer \| null | The user's id, or `null` when there is no authenticated user |
| `email` | string \| null | The user's email, or `null` |
| `is_admin` | boolean | Admin of the **active** organization. Always `true` since Story 21.24 removed the gate |
| `is_global_admin` | boolean | Platform-admin tier. Always `true` for an anonymous caller |

**Errors** — none. The endpoint does not refuse a caller.
