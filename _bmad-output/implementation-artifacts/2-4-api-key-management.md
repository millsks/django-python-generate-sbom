# Story 2.4: API Key Management

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want to create, list, and revoke API keys for my org,
so that developers and CI pipelines can authenticate against the REST API programmatically.

## Acceptance Criteria

1. Given I am an org admin and call `POST /api/v1/keys/` with a `name`, when the key is created, then the response includes the full plaintext key value exactly once; subsequent `GET /api/v1/keys/` shows only the first 8-character prefix plus a masked suffix — the plaintext key is never retrievable again (FR-2.1, AD-8).
2. Given an org already has 10 active (non-revoked) API keys, when I attempt to create an 11th via `POST /api/v1/keys/`, then the response is `400` with `{"error": "This org has reached the maximum of 10 active API keys.", "code": "api_key_limit_reached"}` (FR-2.2).
3. Given I am an org admin and call `DELETE /api/v1/keys/{key_id}/`, when the request is processed, then `OrgApiKey.revoked_at` is set to the current timestamp immediately; any subsequent request using that key returns `401` (FR-2.3).
4. Given `GET /api/v1/keys/` with a valid session or API key scoped to the org, when the request is processed, then the response lists all active (non-revoked) keys with `name`, `prefix`, `created_at`, and `last_used_at` (FR-2.4).
5. Given a DRF request with header `Authorization: Api-Key <valid-key>`, when the custom auth class processes the request, then the request is authenticated, `request.auth` is the `OrgApiKey` instance, `request.auth.org` is the key's org, and `last_used_at` is updated to now (AD-8).
6. Given a DRF request with a revoked or non-existent key in the `Authorization: Api-Key` header, when the request is processed, then the response is `401` with `{"error": "Invalid or revoked API key.", "code": "invalid_api_key"}` (FR-2.5).
7. Given an API request where the authenticated key belongs to Org A and targets a resource owned by Org B, when the request is processed, then the response is `404` — existence of the resource is not disclosed to the requesting org (AD-2, FR-2.6).
8. Given the web UI API key management page viewed by an admin, when the page renders, then a table shows all active keys (name, prefix, created date, last used date) and a "Create key" button is present; the full plaintext key is displayed in a dismissible modal only immediately after creation.
9. Given the web UI API key management page viewed by a non-admin member, when the page renders, then the "Create key" button and "Revoke" controls are absent.

## Tasks / Subtasks

- [ ] Task 1 — `OrgApiKey` model (AC: #1, #3, #5)
  - [ ] `class OrgApiKey(AbstractAPIKey)` from `djangorestframework-api-key`, adding `org` FK(Org), `last_used_at` (nullable), `revoked_at` (nullable)
  - [ ] Rely on the library for key generation, SHA-512 hashing, `prefix` storage, and `get_from_key(raw_key)` — do NOT hand-roll crypto (AD-8)
  - [ ] Generate the migration
- [ ] Task 2 — Custom DRF authentication class (AC: #5, #6)
  - [ ] `OrgApiKeyAuthentication` subclasses the library's `APIKeyAuthentication`/`BaseAPIKeyAuthentication`
  - [ ] Resolve the key via `OrgApiKey.objects.get_from_key(raw_key)`; reject if `revoked_at` is set (→ `401`)
  - [ ] On success: set `request.auth = org_api_key`, update `last_used_at = now()`, expose `request.auth.org`
  - [ ] `401` body uses the standard error envelope with code `invalid_api_key` (AC #6)
  - [ ] Register alongside `SessionAuthentication` in `DEFAULT_AUTHENTICATION_CLASSES` (Story 2.2 seam)
- [ ] Task 3 — Create key (AC: #1, #2)
  - [ ] `POST /api/v1/keys/` (admin only): create the key, return the plaintext value EXACTLY once in the response
  - [ ] Enforce the 10-active-key limit BEFORE creation; over-limit → `400` `api_key_limit_reached` with the exact message (AC #2)
  - [ ] Persist only name, prefix, hashed key, org, timestamps — never the plaintext
- [ ] Task 4 — List keys (AC: #4)
  - [ ] `GET /api/v1/keys/` returns active (non-revoked) keys with name, prefix, created_at, last_used_at — never the hash or plaintext
  - [ ] Scoped to the caller's org via `get_api_keys(org)` selector
- [ ] Task 5 — Revoke key (AC: #3)
  - [ ] `DELETE /api/v1/keys/{key_id}/` (admin only): `revoke_api_key(org, key_id)` sets `revoked_at = now()` (soft delete, preserves audit)
  - [ ] Immediately effective: the auth class rejects revoked keys (`401`). In-flight requests already authenticated complete normally (FR-2.3)
- [ ] Task 6 — Cross-org 404 enforcement (AC: #7)
  - [ ] All key/resource lookups use `.for_org(request.auth.org)` so a key from Org A targeting Org B's resource returns `404` (queryset yields no row) — never `403` on API
- [ ] Task 7 — Web UI key management page (AC: #8, #9)
  - [ ] Admins: table of active keys + "Create key" button; on create, show the plaintext in a dismissible modal ONCE (never re-fetchable)
  - [ ] Non-admins: read-only, no create/revoke controls; server also enforces admin-only mutations
  - [ ] API calls via `frontend/src/api/keys.ts` (AD-5)
- [ ] Task 8 — Tests (AC: all)
  - [ ] Unit: create returns plaintext once; list never returns plaintext/hash
  - [ ] Unit: 11th active key → `400` `api_key_limit_reached` (exact message)
  - [ ] Unit: revoke sets `revoked_at`; a request with the revoked key → `401` `invalid_api_key`
  - [ ] Unit: valid key auth sets `request.auth.org` and updates `last_used_at`
  - [ ] Unit: cross-org resource access with a valid key → `404`
  - [ ] Unit: non-admin blocked from create/revoke
  - [ ] `pixi run cov` ≥90% on the auth class, services, selectors, views

## Dev Notes

### API keys via `AbstractAPIKey` subclass (AD-8 — do not hand-roll crypto)

```python
class OrgApiKey(AbstractAPIKey):
    # inherits: prefix, hashed_key, name, created, revoked
    org: FK(Org)
    last_used_at: datetime | None
    revoked_at: datetime | None
```

`djangorestframework-api-key` generates a random 32-byte key, stores the **SHA-512 hash**, and returns the plaintext once at creation. SHA-512 is correct here — random tokens need fast comparison, not PBKDF2 (which is for passwords). `OrgApiKey.objects.get_from_key(raw_key)` does the lookup. `revoked_at` gives soft revocation that preserves audit history. [Source: solution-design.md §3.1, §10 API key security]

Note: prd NFR-3.3 says "PBKDF2-hashed"; the architecture superseded this with AD-8's SHA-512-via-library decision (PBKDF2 is the wrong tool for random tokens). Follow AD-8 — this divergence is intentional and recorded in the spine.

### Custom auth class (solution-design.md §5.1, AD-8)

```python
# In every DRF view that touches org data (Api-Key path):
org = request.auth.org
```

`OrgApiKeyAuthentication` calls `get_from_key`, rejects revoked keys, updates `last_used_at`, sets `request.auth = org_api_key`. Registered alongside `SessionAuthentication` (Story 2.2) so both web and programmatic clients work. Unauthenticated requests → `401`.

### Auth header convention (spine Consistency Conventions)

`Authorization: Api-Key <key>` on all programmatic API requests. `request.auth` is always the `OrgApiKey` instance; `org = request.auth.org` — never from session or query param on the Api-Key path.

### Org isolation (AD-2, FR-2.6)

Every endpoint returning/modifying org data enforces that the key's org owns the resource. Cross-org or non-existent → `404` on API (existence not disclosed). Use `Model.objects.for_org(org).get(pk=...)` which raises `DoesNotExist` for both cases.

### Services / selectors (solution-design.md §3.1)

```python
# users/services.py
def revoke_api_key(org: Org, key_id: UUID) -> None: ...
# users/selectors.py
def get_api_keys(org: Org) -> QuerySet[OrgApiKey]: ...
```

### Endpoints (solution-design.md §5.2)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/keys/` | Yes | List API keys for org |
| `POST` | `/api/v1/keys/` | Yes | Create API key (admin only) |
| `DELETE` | `/api/v1/keys/{id}/` | Yes | Revoke API key (admin only) |

(Solution-design §5.2 uses `/api/v1/api-keys/`; epics/PRD use `/api/v1/keys/`. Follow the PRD/epics path `/api/v1/keys/` for AC compliance; keep it consistent across backend + `frontend/src/api/keys.ts`.)

### Testing standards

- Unit tests, Django test DB / DRF `APIClient`. Highest-value cases: plaintext-shown-once, 10-key limit, revoke→401, cross-org→404.
- Never assert on or log plaintext keys beyond the single creation-response check.
- ≥90% coverage; mypy strict; structlog binds `org_id` (never the key/hash).

### Constraints / guardrails

- Depends on Stories 2.1 (Org) and 2.2 (DRF auth config seam / admin identity).
- AD-8: no custom crypto in the auth path — library only.
- `djangorestframework-api-key` is a runtime dependency (already anticipated in Story 1.1 pypi-deps) — confirm it's installed.
- Never commit or log secrets; `Authorization` headers excluded from logs (Story 1.3).

### Project Structure Notes

- `OrgApiKey` model + `OrgApiKeyAuthentication` live in `backend/<project_slug>/users/` (solution-design §3.1). The auth class file is shared with Story 2.2's DRF config.
- Web UI: `frontend/src/pages/KeysPage.tsx` (solution-design §7.2) with API calls via `frontend/src/api/keys.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4: API Key Management]
- [Source: ARCHITECTURE-SPINE.md#AD-8 — API key via AbstractAPIKey subclass]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Auth header, Org access in views]
- [Source: solution-design.md#3.1 users/ — OrgApiKey]
- [Source: solution-design.md#5.1 Authentication]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: solution-design.md#10. Security Design — API key security]
- [Source: prd.md#FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-2.5, FR-2.6]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
