# Story 21.7: API Key Management Page

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.6**. Org-scoped by the `OrgMemberRequiredMixin` from Story 21.4.

## Story

As an org member,
I want to create and revoke API keys through a server-rendered page,
so that I can obtain programmatic credentials without the SPA.

## Acceptance Criteria

1. **The keys page is converted.**
   Given `KeysPage.tsx` lists keys and creates them via `/keys/`, when it is converted, then an org-scoped
   page lists the org's active keys with their name, prefix, created date, and `last_used_at`, and creation is
   a crispy form calling the existing key service directly.
2. **A generated key is revealed exactly once.**
   Given `OrgApiKey` extends `AbstractAPIKey` and stores only a hash (**AD-8**, NFR-3.3), so the plaintext key
   is unrecoverable after creation, when a key is created, then the plaintext is displayed **once** on the
   result page with an explicit warning, is **not** written to the session, any log, or any subsequent page
   render, and only the prefix appears in the list thereafter.
3. **Revocation is confirmed and immediate.**
   Given revocation is destructive, when a user revokes a key, then a confirmation step precedes it, the
   revocation is a CSRF-protected POST, `revoked_at` is set, and the revoked key **immediately fails
   authentication** against `/api/v1/` — asserted by a test, not assumed.
4. **Keys are org-scoped.**
   Given keys belong to an org (**AD-2**), when a member of org A requests or attempts to revoke a key
   belonging to org B, then the response is indistinguishable from a non-existent key.
5. **Gate green.**
   When the story completes, then tests cover listing, creation, the one-time reveal, revocation, the
   post-revocation authentication failure, and cross-org denial, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Key list view (AC: #1, #4)** — Org-scoped selector; show prefix and `last_used_at`, never a
  full key.
- [ ] **Task 2 — Create form + one-time reveal (AC: #1, #2)** — Render the plaintext on the POST result page
  only. Do **not** stash it in the session for a redirect.
- [ ] **Task 3 — Revoke with confirmation (AC: #3)** — POST + confirm step.
- [ ] **Task 4 — Tests + gate (AC: #5)** — Include an end-to-end assertion that a revoked key is rejected by
  `OrgApiKeyAuthentication`.

## Dev Notes

### Grounded facts (verified)

- `generate_sbom/users/urls.py` — `keys/` (list, create) and `keys/<str:key_id>/` (revoke).
- **AD-8**: `OrgApiKey` extends `AbstractAPIKey` from `djangorestframework-api-key`, adding `org` FK,
  `last_used_at`, and `revoked_at`; a custom auth class updates `last_used_at` on each authenticated request.
- `base.py:52` — `OrgApiKeyAuthentication` is registered in `DEFAULT_AUTHENTICATION_CLASSES` (a known
  pluggability gap, deliberately **not** fixed in this epic — see the Epic 21 preamble).
- NFR-3.3 requires API key hashing; `AbstractAPIKey` provides it, which is precisely why the plaintext cannot
  be re-displayed later.
- Prior story: 2.4 (API key management).

### The one-time reveal is a correctness constraint, not UX polish

Because only a hash is stored, a key not captured at creation is permanently lost. Render it on the POST
response directly. Stashing it in the session to survive a redirect would put a live credential in the session
store — do not do that, even though it makes POST-redirect-GET tidier.

### Watch for

- **`last_used_at` is written on every authenticated API request** — the list view reads it but must not write.
- **Revoked keys stay listed or disappear?** Match the SPA's current behaviour rather than inventing one;
  verify against `KeysPage.tsx` before choosing.
- **Do not log the plaintext key** anywhere, including structlog debug output.

### Testing standards

- A test that creates a key, captures the plaintext, revokes it, and asserts a subsequent `/api/v1/` request
  with that key returns 401/403.
- A test asserting the plaintext does not appear in a second GET of the keys page.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.7: API Key Management Page]
- `frontend/src/pages/KeysPage.tsx`, `frontend/src/api/keys.ts`,
  `generate_sbom/users/{models,services,authentication,views}.py`.
- Upstream: `21-6-organization-and-member-management-pages.md`.
- Architecture: AD-2 (org isolation), AD-8 (API key model).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
