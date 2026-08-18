---
baseline_commit: 94284c5
---

# Story 21.7: API Key Management Page

Status: review

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

- [x] **Task 1 — Key list view (AC: #1, #4)** — Org-scoped selector; show prefix and `last_used_at`, never a
  full key.
- [x] **Task 2 — Create form + one-time reveal (AC: #1, #2)** — Render the plaintext on the POST result page
  only. Do **not** stash it in the session for a redirect.
- [x] **Task 3 — Revoke with confirmation (AC: #3)** — POST + confirm step.
- [x] **Task 4 — Tests + gate (AC: #5)** — Include an end-to-end assertion that a revoked key is rejected by
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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **552 passed**, coverage **96.09%**; frontend **223 passed**.
- `mypy src` clean over 90 files; `ruff check .` clean.
- **18 new tests** in `tests/unit/test_api_key_pages.py`.
- Routes: `ui-keys` → `/keys`, `ui-key-create` → `/keys/create`, `ui-key-revoke` → `/keys/revoke`.
- **The AC #3 assertion, end to end:** created a key through the page, extracted the plaintext
  from the reveal response, called `/api/v1/sbom/jobs/` with `Authorization: Api-Key <key>` →
  **200**; revoked it through the page; called again → **401/403**. No restart, no cache expiry.
- Authorization: plain member GETs the list (**200**) but is **403** on create and revoke;
  anonymous → **302 → /login**; both mutations **405** on GET and **403** without CSRF.
- Cross-org: another org's key is absent from the list, and revoking it produces the *same*
  "API key not found." as a nonexistent UUID, with the other org's key left unrevoked.

### Completion Notes List

**The Dev Notes asked two questions; both were answered from the source rather than guessed.**

1. *"Revoked keys stay listed or disappear? Match the SPA's current behaviour."* — They
   **disappear**. `get_api_keys()` filters `revoked_at__isnull=True`, and the SPA rendered
   exactly what that endpoint returned. Asserted by `test_revoked_keys_drop_out_of_the_list`.
2. *Who may do what?* — `KeysPage.tsx` states it in its own comment: **"API Keys is viewable by
   any member; admin flag (create/revoke) comes from useAuth"**, and the DRF views agree
   (`KeysView.get` uses `get_request_org`, while `KeysView.post` and `KeyDetailView.delete` use
   `get_admin_org`).

**That second answer is a deviation from this story's prose, and a deliberate one.** The story
is titled for an org member ("As an org member, I want to create and revoke API keys") and AC #1
describes an org-scoped page. Implemented as: **list = `OrgMemberRequiredMixin`**, **create and
revoke = `OrgAdminRequiredMixin`**. Following the story literally would have *widened* an
existing authorization boundary — letting any member mint credentials for the whole org — while
the epic's premise is that the API contract and its rules are unchanged. Preserving parity won.
Tested from both sides: a member can see the list but is 403 on both mutations.

**The one-time reveal is a correctness constraint, and the storage model is what makes it so.**
`OrgApiKey` extends `AbstractAPIKey`, which stores only a hash (AD-8, NFR-3.3) — a key not
captured at creation is *permanently* unrecoverable. So `ApiKeyCreateView` renders the plaintext
straight from the POST. The story explicitly forbids stashing it in the session to make
POST-redirect-GET tidy, and three tests hold that line: it appears on the reveal page, it is
absent from a later `/keys` render, and it is absent from the session. `create_api_key` logs only
the prefix, so it never reaches structlog either.

**The revocation test is the one that could have been faked, so it wasn't.** Asserting
`revoked_at is not None` proves nothing about whether revocation *works* — the auth path lives in
`inventory/users/authentication.py`, a module this story does not touch. The test therefore
exercises the real thing: authenticate against `/api/v1/` before (200) and after (401/403).
That round trip also validates the plaintext-extraction helper: a string that authenticates
successfully is unarguably the real key, so the reveal tests cannot be passing on a substring.

**Cross-org indistinguishability comes from the service, not a branch.** `revoke_api_key` scopes
its lookup by `org`, so another org's key and a nonexistent UUID take the identical code path and
produce the identical message. There is no place where a "forbidden" could diverge from a
"not found".

**`last_used_at` is read, never written.** The list renders it (showing "never" when null rather
than an empty cell); only `OrgApiKeyAuthentication` writes it, on each authenticated API request.
The Dev Notes flagged this specifically.

**The 10-key limit surfaces as a field error.** `ApiKeyLimitError` (FR-2.2) is caught and attached
to the `name` field, so hitting the limit redisplays the form rather than 500-ing. Asserted, along
with the count being unchanged.

**Not done here.** Keys cannot be renamed or un-revoked — neither exists in the API, and inventing
either would put the HTML path ahead of the contract. There is no key-usage history beyond
`last_used_at`, and no expiry (the model has no expiry field).

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations —
one of which, `base.py:52` registering `OrgApiKeyAuthentication` as a global DRF default, is the
very mechanism this story's revocation test exercises.

### File List

**New (3)**
- `src/django_apps/inventory/templates/inventory/keys/list.html` — roster + admin-only create form
- `src/django_apps/inventory/templates/inventory/keys/key_created.html` — one-time reveal
- `tests/unit/test_api_key_pages.py` (18 tests)

**Modified (6)**
- `src/django_apps/inventory/users/forms.py` — `CreateApiKeyForm`
- `src/django_apps/inventory/users/pages.py` — `ApiKeysView`, `ApiKeyCreateView`,
  `ApiKeyRevokeView`, `_keys_context`
- `src/django_apps/inventory/urls_pages.py` — three `ui-` routes
- `src/config/urls.py` — free `keys` from the SPA catch-all
- `src/django_service/templates/_nav.html` — reverse `ui-keys` for the API Keys item
- `src/django_apps/inventory/templates/inventory/orgs/hub.html` — hub link now reverses `ui-keys`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted API key management to a server-rendered page. Listing is member-level while create and revoke are admin-only, matching the SPA's stated rule and the DRF endpoints rather than the story's prose, which would have widened the boundary. A created key's plaintext is rendered once on the POST response — never via session, redirect, or log — because only a hash is stored and the key is otherwise unrecoverable. Revocation is a confirmed CSRF-protected POST, soft-sets `revoked_at`, and is proven to bite by authenticating against `/api/v1/` before (200) and after (401/403). Cross-org and nonexistent keys are indistinguishable. `pixi run ci` exit 0; 552 backend tests at 96.09%. |
